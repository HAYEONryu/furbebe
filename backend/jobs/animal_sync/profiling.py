"""CLI for live capture and deterministic offline profiling. No DB or FastAPI."""

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter
from datetime import UTC, date, datetime
from pathlib import Path

from .client import ENDPOINT, AnimalApiClient, ApiFailure, Redactor, load_service_key
from .field_stats import canonical, identifier, parse_date, text
from .metrics import apply_reference_results, build_profile
from .reports import write_reports
from .source_models import normalize_items
from .status_policy import korea_today

ROOT = Path(__file__).resolve().parents[3]


def local_path(root: Path, requested: Path) -> Path:
    allowed = (root / ".local" / "profiling").resolve()
    # Do not permit redirecting the entire local output tree via a symlink/junction.
    if not allowed.is_relative_to(root.resolve()):
        raise ApiFailure("UNSAFE_OUTPUT_PATH")
    target = (root / requested).resolve() if not requested.is_absolute() else requested.resolve()
    if not target.is_relative_to(allowed):
        raise ApiFailure("OUTPUT_MUST_BE_UNDER_LOCAL_PROFILING")
    return target


def check_git_exclusion(root: Path):
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", "--", ".local/profiling/probe.jsonl"],
        cwd=root,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise ApiFailure("RAW_DIRECTORY_NOT_GIT_IGNORED")
    tracked = subprocess.run(
        ["git", "ls-files", "-z", "--", ".env", ".local"],
        cwd=root,
        capture_output=True,
        check=False,
    )
    if tracked.returncode or tracked.stdout:
        raise ApiFailure("SECRET_OR_RAW_PATH_ALREADY_TRACKED")


def collect(
    client,
    raw_path,
    *,
    run_id,
    target=20000,
    page_size=100,
    max_pages=2000,
    filters=None,
    entire_population=False,
    progress=None,
):
    run = {
        "run_id": run_id,
        "started_at": datetime.now(UTC).isoformat(),
        "endpoint": ENDPOINT,
        "query_without_key": filters or {},
        "target_unique_dogs": target,
        "page_size": page_size,
        "requested_pages": 0,
        "successful_pages": 0,
        "failed_pages": 0,
        "failed_page_numbers": [],
        "reported_total_counts": [],
        "observed_shapes": {},
        "header_observations": {},
        "entire_population_scope": entire_population,
        "exhausted": False,
        "stop_reason": None,
        "raw_file": raw_path.name,
    }
    rows, seen, dog_ids, fingerprints = [], set(), set(), set()
    shapes, headers = (
        Counter(),
        {f: Counter() for f in ("reqNo", "resultCode", "resultMsg", "errorMsg")},
    )
    page_sizes = Counter()
    try:
        with raw_path.open("x", encoding="utf-8") as raw:
            for page_number in range(1, max_pages + 1):
                run["requested_pages"] += 1
                try:
                    page = client.fetch(page_number, page_size, filters=filters)
                except ApiFailure as exc:
                    run["failed_pages"] += 1
                    run["failed_page_numbers"].append(page_number)
                    run["stop_reason"] = str(exc)
                    break
                run["successful_pages"] += 1
                run["reported_total_counts"].append(page.total)
                shapes[page.shape] += 1
                page_sizes[str(page.page_size)] += 1
                for name in headers:
                    value = page.header.get(name)
                    # reqNo is an opaque request identifier; measure presence/type, not raw value.
                    label = (
                        "missing"
                        if name not in page.header
                        else "null"
                        if value is None
                        else "blank"
                        if value == ""
                        else "present:" + type(value).__name__
                        if name == "reqNo"
                        else client.redactor.text(value, personal=True)[:160]
                    )
                    headers[name][label] += 1
                raw.write(
                    json.dumps(
                        {
                            "page_number": page_number,
                            "fetched_at": datetime.now(UTC).isoformat(),
                            "response": page.envelope,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                raw.flush()
                if not page.items:
                    run["exhausted"] = len(rows) == page.total
                    run["stop_reason"] = (
                        "exhausted" if run["exhausted"] else "unexpected_empty_page"
                    )
                    break
                digest = hashlib.sha256(canonical(page.items).encode()).hexdigest()
                # Keep repeated pages in raw/row counts to expose the source problem.
                repeated = digest in fingerprints
                fingerprints.add(digest)
                rows.extend(page.items)
                for row in page.items:
                    if (key := identifier(row)) is not None:
                        seen.add(key)
                        if text(row.get("upKindNm")) == "개":
                            dog_ids.add(key)
                if progress:
                    progress(
                        {
                            "page": page_number,
                            "raw_count": len(rows),
                            "unique_all": len(seen),
                            "unique_dogs": len(dog_ids),
                        }
                    )
                if repeated:
                    run["stop_reason"] = "repeated_page"
                    break
                if len(set(run["reported_total_counts"])) > 1:
                    run["stop_reason"] = "totalCount_changed"
                    break
                if len(rows) >= page.total:
                    # Verify the next page really is empty before claiming exhaustive pagination.
                    continue
                if len(dog_ids) >= target:
                    run["stop_reason"] = "target_reached"
                    break
            else:
                run["stop_reason"] = "page_limit"
    except KeyboardInterrupt:
        run["stop_reason"] = "interrupted"
        run["failed_pages"] += 1
    finally:
        run.update(
            finished_at=datetime.now(UTC).isoformat(),
            request_attempts=client.attempts,
            retries=client.retries,
            errors=dict(client.errors),
            observed_shapes=dict(shapes),
            header_observations={k: dict(v) for k, v in headers.items()},
            observed_page_sizes=dict(page_sizes),
        )
    return rows, run


def load_capture(path: Path):
    metadata = path.parent / "run.json"
    run = json.loads(metadata.read_text(encoding="utf-8"))
    if run.get("raw_file") != path.name:
        raise ApiFailure("CAPTURE_METADATA_MISMATCH")
    expected_hash = run.get("raw_sha256")
    actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    if expected_hash and expected_hash != actual_hash:
        raise ApiFailure("CAPTURE_HASH_MISMATCH")
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            item = json.loads(line)
            payload = item["response"]["response"]["body"]
            values, _ = normalize_items(payload)
            rows.extend(value.root for value in values)
    return rows, run


def parser():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--target-unique", type=int, default=20000)
    cli.add_argument("--min-unique", type=int, default=5000)
    cli.add_argument("--page-size", type=int, default=100)
    cli.add_argument("--max-pages", type=int, default=2000)
    cli.add_argument("--request-interval", type=float, default=1.0)
    cli.add_argument("--seed", type=int, default=20260911)
    cli.add_argument("--output-dir", type=Path, default=Path(".local/profiling"))
    cli.add_argument("--start-date", help="YYYYMMDD; paired with --end-date")
    cli.add_argument("--end-date", help="YYYYMMDD; paired with --start-date")
    cli.add_argument(
        "--entire-population-confirmed",
        action="store_true",
        help="Use only after verifying this query covers the true entire population.",
    )
    cli.add_argument(
        "--input", type=Path, help="Replay a local raw capture; no network/key required."
    )
    cli.add_argument(
        "--check-config", action="store_true", help="Print key presence only; no request."
    )
    cli.add_argument("--probe", action="store_true", help="One row; save local envelope only.")
    return cli


def main(argv=None):
    cli = parser()
    args = cli.parse_args(argv)
    if args.min_unique < 5000 or args.target_unique < args.min_unique:
        cli.error("min-unique must be >=5000 and target-unique >= min-unique")
    if not 1 <= args.page_size <= 1000 or args.max_pages < 1 or args.request_interval < 0:
        cli.error("invalid page-size, max-pages or request-interval")
    if bool(args.start_date) != bool(args.end_date):
        cli.error("start-date and end-date must be supplied together")
    filters = {}
    if args.start_date:
        start, end = parse_date(args.start_date), parse_date(args.end_date)
        if start is None or end is None or start > end:
            cli.error("invalid date range")
        filters = {"bgnde": args.start_date, "endde": args.end_date}
    if filters and args.entire_population_confirmed:
        cli.error("a bounded date range cannot establish the entire-population exception")
    try:
        if args.check_config:
            try:
                load_service_key(ROOT)
                configured = True
            except ApiFailure:
                configured = False
            print(json.dumps({"service_key_configured": configured}))
            return 0 if configured else 2
        output = local_path(ROOT, args.output_dir)
        check_git_exclusion(ROOT)
        if args.input:
            raw_path = local_path(ROOT, args.input)
            rows, run = load_capture(raw_path)
            run["analysis_mode"] = "offline_replay"
            redactor = Redactor()
            output = raw_path.parent
        else:
            key = load_service_key(ROOT)
            run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
            output = output / run_id
            output.mkdir(parents=True, exist_ok=False)
            raw_path = output / f"raw-{run_id}.jsonl"
            redactor = Redactor(key)
            with AnimalApiClient(key, interval=args.request_interval) as client:
                if args.probe:
                    page = client.fetch(1, 1, filters=filters)
                    (output / "probe.json").write_text(
                        json.dumps(page.envelope, ensure_ascii=False), encoding="utf-8"
                    )
                    print(
                        json.dumps(
                            {
                                "probe": "success",
                                "shape": page.shape,
                                "rows": len(page.items),
                                "totalCount": page.total,
                                "saved_under": str(output),
                            }
                        )
                    )
                    return 0
                rows, run = collect(
                    client,
                    raw_path,
                    run_id=run_id,
                    target=args.target_unique,
                    page_size=args.page_size,
                    max_pages=args.max_pages,
                    filters=filters,
                    entire_population=args.entire_population_confirmed,
                    progress=lambda p: print(json.dumps(p), flush=True),
                )
            run["raw_sha256"] = hashlib.sha256(raw_path.read_bytes()).hexdigest()
            run["as_of_date"] = korea_today().isoformat()
            run["seed"] = args.seed
            (output / "run.json").write_text(
                json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        if not rows:
            print(
                json.dumps(
                    {
                        "status": "blocked",
                        "reason": run.get("stop_reason"),
                        "run_directory": str(output),
                    }
                )
            )
            return 2
        summary, selected = build_profile(
            rows,
            run,
            redactor,
            today=date.fromisoformat(run["as_of_date"]),
            minimum=args.min_unique,
            seed=run.get("seed", args.seed),
        )
        reference_file = output / "reference-profile.json"
        if reference_file.exists():
            apply_reference_results(summary, json.loads(reference_file.read_text(encoding="utf-8")))
        write_reports(ROOT, output, summary, selected, redactor)
        print(
            json.dumps(
                {
                    "status": "blocked" if summary["blockers"] else "complete",
                    "unique_animals": summary["items"]["unique_desertion_no_count"],
                    "unique_dogs": summary["species"]["dog_count"],
                    "blockers": summary["blockers"],
                    "run_directory": str(output),
                }
            )
        )
        return 2 if summary["blockers"] else 0
    except ApiFailure as exc:
        print(json.dumps({"status": "blocked", "reason": str(exc)}), file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError, TypeError):
        # Never print exception text from input data or authenticated HTTP requests.
        print(
            json.dumps({"status": "blocked", "reason": "LOCAL_IO_OR_ANALYSIS_ERROR"}),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
