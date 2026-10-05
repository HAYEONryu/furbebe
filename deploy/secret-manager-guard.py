"""Best-effort monthly Secret Manager access cutoff; never reads secret payloads.

Uses gcloud's short-lived identity. Dry-run unless --apply is explicitly set.
This is NOT a billing cap: monitoring/scheduling lag and storage charges remain.
"""
import argparse
import json
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

MONTH = "furbebe_guard_month"
VERSIONS = "furbebe_guard_versions"


def month_window(now):
    local = now.astimezone(ZoneInfo("America/Los_Angeles"))
    first = local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # Include an extra hour to avoid undercounting a boundary-aligned delta.
    start = first.astimezone(timezone.utc) - timedelta(hours=1)
    return local.strftime("%Y-%m"), start.isoformat(), now.isoformat()


class Api:
    def __init__(self):
        self.token = subprocess.check_output(
            ["gcloud", "auth", "print-access-token"], text=True
        ).strip()

    def call(self, method, url, query=None, body=None):
        if query:
            url += "?" + urllib.parse.urlencode(query)
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(url, data=data, method=method, headers={
            "Authorization": "Bearer " + self.token,
            "Content-Type": "application/json",
        })
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            # Do not print response bodies, credentials, or secret values.
            raise RuntimeError(f"Google API {method} failed with HTTP {exc.code}") from None


def request_count(api, project, start, end):
    url = f"https://monitoring.googleapis.com/v3/projects/{project}/timeSeries"
    params = {
        "filter": 'metric.type="serviceruntime.googleapis.com/api/request_count" '
                  'AND resource.type="consumed_api" '
                  'AND resource.labels.service="secretmanager.googleapis.com" '
                  f'AND resource.labels.project_id="{project}"',
        "interval.startTime": start, "interval.endTime": end,
        "aggregation.alignmentPeriod": "3600s",
        "aggregation.perSeriesAligner": "ALIGN_SUM",
        "aggregation.crossSeriesReducer": "REDUCE_SUM",
        "view": "FULL", "pageSize": 1000,
    }
    total, samples, tokens = 0, 0, set()
    while True:
        page = api.call("GET", url, query=params)
        for series in page.get("timeSeries", []):
            for point in series.get("points", []):
                number = int(point["value"]["int64Value"])
                if number < 0:
                    raise RuntimeError("Negative request count; refusing to act")
                total += number
                samples += 1
        token = page.get("nextPageToken")
        if not token:
            break
        if token in tokens:
            raise RuntimeError("Repeated Monitoring page token")
        tokens.add(token)
        params["pageToken"] = token
    if not samples:
        raise RuntimeError("No usage samples: do not treat missing data as zero; no state changed")
    return total


def run(api, project, secret_id, threshold=8000, apply=False, now=None):
    if not 1 <= threshold <= 9000:
        raise ValueError("Threshold must leave headroom: 1..9000")
    now = now or datetime.now(timezone.utc)
    month, start, end = month_window(now)
    resource = f"projects/{project}/secrets/{secret_id}"
    url = "https://secretmanager.googleapis.com/v1/" + resource
    secret = api.call("GET", url)
    # Google canonicalizes project IDs to project numbers in response names.
    canonical = secret.get("name", "")
    parts = canonical.split("/")
    if (len(parts) != 4 or parts[0] != "projects" or parts[2] != "secrets"
            or parts[3] != secret_id
            or parts[1] not in (project, "552862841310")):
        raise RuntimeError("Unexpected secret resource")
    resource = canonical
    url = "https://secretmanager.googleapis.com/v1/" + resource
    labels = dict(secret.get("labels", {}))
    original_ids = labels.get(VERSIONS, "")
    if bool(labels.get(MONTH)) != bool(original_ids):
        raise RuntimeError("Incomplete guard marker; manual review required")
    managed = original_ids.split("_") if original_ids else []
    if any(not value.isdigit() for value in managed):
        raise RuntimeError("Invalid guard version marker")
    if labels.get(MONTH, "") > month:
        raise RuntimeError("Guard marker is in a future month; refusing to restore")

    versions, page_token, seen = {}, None, set()
    while True:
        query = {"pageSize": 100}
        if page_token:
            query["pageToken"] = page_token
        page = api.call("GET", url + "/versions", query=query)
        for version in page.get("versions", []):
            if not version["name"].startswith(resource + "/versions/"):
                raise RuntimeError("Unexpected version resource")
            versions[version["name"].rsplit("/", 1)[1]] = version
        page_token = page.get("nextPageToken")
        if not page_token:
            break
        if page_token in seen:
            raise RuntimeError("Repeated Secret Manager page token")
        seen.add(page_token)

    # Counts all API methods conservatively, including free management requests.
    count = request_count(api, project, start, end)
    hold = labels.get(MONTH) == month or count >= threshold
    enabled = [key for key, value in versions.items() if value["state"] == "ENABLED"]
    billable_versions = sum(v["state"] in ("ENABLED", "DISABLED") for v in versions.values())
    result = {"month": month, "requests": count, "threshold": threshold,
              "billable_versions_in_target": billable_versions,
              "apply": apply, "target": resource}

    def write_labels(new_labels):
        nonlocal secret
        if not secret.get("etag"):
            raise RuntimeError("Missing secret etag; refusing unprotected metadata update")
        secret = api.call("PATCH", url, query={"updateMask": "labels"}, body={
            "name": resource, "labels": new_labels, "etag": secret["etag"]})

    if hold:
        marked = sorted(set(managed + enabled), key=int)
        if not marked:
            return dict(result, action="already_disabled_no_guard_ownership")
        encoded = "_".join(marked)
        if len(encoded) > 63:
            raise RuntimeError("Too many version IDs for durable marker; manual review required")
        result.update(action="block", versions=enabled)
        if apply:
            # Persist intent before disabling: a partial failure resumes next run.
            updated = dict(labels, **{MONTH: month, VERSIONS: encoded})
            if updated != labels:
                write_labels(updated)
            for key in enabled:
                version = versions[key]
                api.call("POST", "https://secretmanager.googleapis.com/v1/" +
                         version["name"] + ":disable", body={"etag": version["etag"]})
        return result

    if managed:
        missing = set(managed) - versions.keys()
        if missing:
            raise RuntimeError("Marked versions missing; manual review required")
        restore = [key for key in managed if versions[key]["state"] == "DISABLED"]
        result.update(action="restore", versions=restore)
        if apply:
            for key in restore:
                version = versions[key]
                api.call("POST", "https://secretmanager.googleapis.com/v1/" +
                         version["name"] + ":enable", body={"etag": version["etag"]})
            # Never restore versions disabled before this guard took ownership.
            updated = {k: v for k, v in labels.items() if k not in (MONTH, VERSIONS)}
            write_labels(updated)
        return result
    return dict(result, action="allow")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default="furbebe-backend")
    parser.add_argument("--secret", default="DATABASE_URL_prod")
    parser.add_argument("--threshold", type=int, default=8000)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(Api(), args.project, args.secret, args.threshold, args.apply), ensure_ascii=False))
