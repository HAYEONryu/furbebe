"""Real local HTTP -> Supabase DEV SQL smoke checks. No writes, fixtures, or migrations.

Run: python -m backend.jobs.read_api_verification
Only aggregates and test outcomes are saved to .local/phase5/dev-api-verification.json.
"""

import hashlib
import json
import socket
import threading
import time
from datetime import UTC, datetime

import httpx
import uvicorn
from sqlalchemy import event, text

from backend.app.core.config import ROOT
from backend.app.core.database_target import get_dev_database_settings
from backend.app.db.models import Base
from backend.app.db.session import create_database_engine
from backend.app.main import create_app
from backend.jobs.animal_sync.verification import data_integrity, preflight


class VerificationFailure(Exception):
    pass


def require(condition, label):
    if not condition:
        raise VerificationFailure(label)


def database_snapshot(engine):
    with (
        engine.connect().execution_options(
            isolation_level="REPEATABLE READ", postgresql_readonly=True
        ) as connection,
        connection.begin(),
    ):
        result = {"preflight": preflight(connection), "integrity": data_integrity(connection)}
        require(connection.scalar(text("SHOW transaction_read_only")) == "on", "read_only_snapshot")
        digests = {}
        for name in sorted(Base.metadata.tables):
            # Identifiers are from application metadata, never caller input.
            key = "key" if name == "tags" else "id"
            digests[name] = connection.scalar(
                text(
                    f"SELECT md5(string_agg(md5(row_to_json(t)::text), '' ORDER BY t.\"{key}\")) "
                    f'FROM public."{name}" t'
                )
            )
        result["domain_digest"] = hashlib.sha256(
            json.dumps(digests, sort_keys=True).encode()
        ).hexdigest()
        return result


def verify():
    settings = get_dev_database_settings()
    engine = create_database_engine(settings)
    server = worker = sock = observed_engine = None
    sql_events = []
    report = {
        "checked_at": datetime.now(UTC).isoformat(),
        "target": "supabase_dev",
        "transport": "HTTP over loopback TCP to Uvicorn",
        "requests": [],
    }

    def observe(connection, cursor, statement, parameters, context, executemany):
        kind = statement.lstrip().split(None, 1)[0].upper()
        require(kind in {"SELECT", "WITH"}, "unexpected_non_read_statement")
        sql_events.append(
            {"read_only": bool(connection.get_execution_options().get("postgresql_readonly"))}
        )

    try:
        before = database_snapshot(engine)
        require(before["preflight"]["alembic_revisions"] == ["20260915_0001"], "expected_schema")
        require(before["integrity"]["counts"]["animals"] > 24, "enough_dev_animals")
        app = create_app(settings)
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        address = "http://127.0.0.1:" + str(sock.getsockname()[1])
        server = uvicorn.Server(uvicorn.Config(app, log_level="critical", access_log=False))
        worker = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
        worker.start()
        deadline = time.monotonic() + 10
        while not server.started and worker.is_alive() and time.monotonic() < deadline:
            time.sleep(0.05)
        require(server.started, "http_server_started")
        observed_engine = app.state.database.engine
        event.listen(observed_engine, "before_cursor_execute", observe)

        with httpx.Client(base_url=address, timeout=30) as client:

            def get(label, path, *, params=None, status=200):
                sql_events.clear()
                started = time.perf_counter()
                response = client.get(path, params=params)
                elapsed = round((time.perf_counter() - started) * 1000, 2)
                report["requests"].append(
                    {
                        "check": label,
                        "status": response.status_code,
                        "milliseconds": elapsed,
                        "sql_queries": len(sql_events),
                    }
                )
                require(response.status_code == status, label)
                require(bool(response.headers.get("x-request-id")), label + "_request_id")
                require(
                    response.headers.get("content-type") == "application/json; charset=utf-8",
                    label + "_content_type",
                )
                require(
                    "raw_payload" not in response.text and "is_favorite" not in response.text,
                    label + "_private_fields",
                )
                if label != "health":
                    require(all(item["read_only"] for item in sql_events), label + "_read_only")
                if status != 200:
                    require(
                        response.json()["error"]["request_id"] == response.headers["x-request-id"],
                        label + "_error_id",
                    )
                return response.json()

            get("health", "/health")
            first = get("list_cold", "/api/v1/animals")
            require(len(first["items"]) == 24, "list_default_size")
            require(
                first["pagination"]["total"] == before["integrity"]["counts"]["animals"],
                "list_total",
            )
            source = first["items"][0]
            detail_path = "/api/v1/animals/" + source["id"]
            get("list_one", "/api/v1/animals", params={"page_size": 1})
            second = get("page_two", "/api/v1/animals", params={"page": 2})
            require(
                not (
                    {row["id"] for row in first["items"]} & {row["id"] for row in second["items"]}
                ),
                "pagination_no_overlap",
            )
            for index in range(2):
                get("list_warm_" + str(index + 1), "/api/v1/animals")
            detail = get("detail_cold", detail_path)
            require(detail["id"] == source["id"], "detail_identity")
            get("detail_warm", detail_path)
            meta = get("meta_cold", "/api/v1/meta/filters")
            get("meta_warm", "/api/v1/meta/filters")
            similar = get("similar_cold", detail_path + "/similar")
            get("similar_warm", detail_path + "/similar")
            require(
                len(similar["items"]) == 4
                and all(
                    item["id"] != source["id"] and "score" not in item for item in similar["items"]
                ),
                "similar_policy",
            )
            tags = get("tags", "/api/v1/tags")
            require(bool(tags["items"]), "tag_catalog_present")
            stats = get("stats", "/api/v1/stats/overview")
            require(
                set(stats)
                == {"animals_total", "new_today", "with_primary_image", "last_synced_at"},
                "stats_contract",
            )
            require(stats["animals_total"] == first["pagination"]["total"], "stats_total")

            for field in ("breed", "sex", "size_group", "age_group", "process_state"):
                if source[field] is not None:
                    filtered = get(
                        "filter_" + field, "/api/v1/animals", params={field: source[field]}
                    )
                    require(
                        bool(filtered["items"])
                        and all(row[field] == source[field] for row in filtered["items"]),
                        "filter_values_" + field,
                    )
            if detail["animal"]["neutered"] is not None:
                get(
                    "filter_neutered",
                    "/api/v1/animals",
                    params={"neutered": detail["animal"]["neutered"]},
                )
            region = next((region for region in meta["regions"] if region["sigungu"]), None)
            require(region is not None, "regions_available")
            for params in (
                {"sido": region["sido"]},
                {"sido": region["sido"], "sigungu": region["sigungu"][0]},
            ):
                filtered = get(
                    "filter_region_" + str(len(params)), "/api/v1/animals", params=params
                )
                require(bool(filtered["items"]), "region_meta_roundtrip")
            if source["breed"]:
                get("search", "/api/v1/animals", params={"q": source["breed"][:50]})
            chosen = next((item for item in first["items"] if len(item["tags"]) >= 2), None)
            require(chosen is not None, "tag_filter_source")
            selected = [tag["key"] for tag in chosen["tags"][:2]]
            for match in ("any", "all"):
                filtered = get(
                    "tag_" + match,
                    "/api/v1/animals",
                    params=[("tag", key) for key in selected] + [("tag_match", match)],
                )
                require(filtered["pagination"]["total"] > 0, "tag_matches_" + match)
            get("tags_type", "/api/v1/tags", params={"type": "fact"})
            for sort in (
                "recent",
                "notice_end",
                "weight_asc",
                "weight_desc",
                "age_youngest",
                "age_oldest",
            ):
                get("sort_" + sort, "/api/v1/animals", params={"sort": sort})
            empty = get("empty", "/api/v1/animals", params={"breed": "__furbebe_absent_smoke__"})
            require(empty["items"] == [] and empty["pagination"]["total"] == 0, "empty_contract")
            get("not_found", "/api/v1/animals/00000000-0000-0000-0000-000000000000", status=404)
            get("invalid_uuid", "/api/v1/animals/invalid", status=422)
            get("invalid_page_size", "/api/v1/animals", params={"page_size": 61}, status=422)
            get(
                "unknown_tag",
                "/api/v1/animals",
                params={"tag": "__furbebe_absent_smoke__"},
                status=404,
            )
            counts = {item["check"]: item["sql_queries"] for item in report["requests"]}
            require(counts["list_one"] == counts["list_cold"] == 4, "no_n_plus_one")
            report["stats"] = stats
            report["meta_counts"] = {name: len(items) for name, items in meta.items()}

        after = database_snapshot(engine)
        require(before["domain_digest"] == after["domain_digest"], "domain_data_unchanged")
        require(
            all(value == 0 for value in after["integrity"]["violations"].values()),
            "domain_integrity",
        )
        report.update(
            status="success",
            domain_data_unchanged=True,
            integrity=after["integrity"],
            all_domain_sql_read_only=True,
        )
        return report
    finally:
        if observed_engine is not None:
            event.remove(observed_engine, "before_cursor_execute", observe)
        if server is not None:
            server.should_exit = True
        if worker is not None:
            worker.join(timeout=10)
        if sock is not None:
            sock.close()
        engine.dispose()


def main():
    output = (ROOT / ".local" / "phase5").resolve()
    try:
        require(output.is_relative_to(ROOT), "local_output_directory")
        report = verify()
    except Exception as exc:
        report = {
            "status": "failed",
            "check": str(exc)
            if isinstance(exc, VerificationFailure)
            else "DEV_HTTP_VERIFICATION_ERROR",
        }
    output.mkdir(parents=True, exist_ok=True)
    (output / "dev-api-verification.json").write_text(
        json.dumps(report, ensure_ascii=True, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=True))
    return 0 if report["status"] == "success" else 2


if __name__ == "__main__":
    raise SystemExit(main())
