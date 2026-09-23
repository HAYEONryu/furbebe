"""Evaluate Phase 8.5 against explicit human labels, never profiling keyword flags."""

import argparse
import csv
import hashlib
import json
from collections import Counter
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from .tagger.behavior import (
    GENERATOR,
    RELEASE_BASIS,
    RELEASED_RULE_IDS,
    RULES,
    VERSION,
    generate_behavior_tags,
    match_candidates,
)
from .tagger.catalog import CATALOG

SOURCE_FIELDS = ("specialMark", "sfeSoci", "sfeHealth", "etcBigo", "adptnTxt")
TRAIT_KEYS = frozenset(row["key"] for row in CATALOG if row["type"] == "trait")
LABELS = {row["key"]: row["label"] for row in CATALOG}
MIN_TRUE_POSITIVES = 5


def digest(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def source_digest(row):
    content = json.dumps(
        {field: row.get(field) for field in SOURCE_FIELDS}, ensure_ascii=False, sort_keys=True
    )
    return hashlib.sha256(content.encode()).hexdigest()


def load_sample(raw_path, sample_path):
    with Path(sample_path).open(encoding="utf-8-sig", newline="") as handle:
        sample = list(csv.DictReader(handle))
    ids = [row["desertionNo"] for row in sample]
    if len(ids) != 100 or len(set(ids)) != 100:
        raise ValueError("Expected 100 distinct manual-review source IDs")
    wanted, rows = set(ids), {}
    with Path(raw_path).open(encoding="utf-8") as handle:
        for line in handle:
            items = json.loads(line)["response"]["response"]["body"]["items"]
            items = items.get("item", []) if isinstance(items, dict) else []
            for row in items if isinstance(items, list) else [items]:
                key = row.get("desertionNo")
                if key not in wanted:
                    continue
                if key in rows:
                    raise ValueError("Duplicate source ID in profiling capture")
                rows[key] = row
    if set(rows) != wanted:
        raise ValueError("Manual-review sample does not match profiling capture")
    return [{**rows[item["desertionNo"]], "stratum": item["stratum"]} for item in sample]


def normalized_values(row):
    return {
        "special_mark": row.get("specialMark"),
        "social_text": row.get("sfeSoci"),
        "health_text": row.get("sfeHealth"),
        "raw_payload": row,
    }


def export_label_template(path, rows):
    """Never overwrite a reviewed file or prefill human labels from predictions."""
    columns = [
        "desertionNo",
        "stratum",
        *SOURCE_FIELDS,
        "source_sha256",
        "candidate_tags",
        "candidate_labels",
        "candidate_evidence",
        "released_tags",
        "generator",
        "generator_version",
        "release_status",
        "human_tags",
        "reviewed_by",
        "reviewed_at",
        "review_notes",
    ]
    with Path(path).open("x", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            export = {key: row.get(key, "") for key in columns}
            export["source_sha256"] = source_digest(row)
            candidates = match_candidates(normalized_values(row))
            export["candidate_tags"] = json.dumps(
                sorted({tag.tag_key for tag in candidates}),
                ensure_ascii=False,
            )
            export["candidate_labels"] = json.dumps(
                [LABELS[key] for key in sorted({tag.tag_key for tag in candidates})],
                ensure_ascii=False,
            )
            export["candidate_evidence"] = json.dumps(
                [asdict(tag) for tag in candidates],
                ensure_ascii=False,
                default=str,
            )
            export.update(
                generator=GENERATOR,
                generator_version=VERSION,
                release_status=RELEASE_BASIS,
                released_tags=json.dumps(
                    sorted(tag.tag_key for tag in generate_behavior_tags(normalized_values(row)))
                ),
            )
            # These are spreadsheet display cells only. Evaluation reloads raw text.
            for key, value in export.items():
                if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
                    export[key] = "'" + value
            writer.writerow(export)


def load_labels(path, rows):
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        labels = list(csv.DictReader(handle))
    source = {row["desertionNo"]: row for row in rows}
    if len(labels) != 100 or {row["desertionNo"] for row in labels} != set(source):
        raise ValueError("Labels must cover exactly the same 100 animals")
    truth = {}
    for row in labels:
        key = row["desertionNo"]
        if not row.get("reviewed_by", "").strip() or not row.get("reviewed_at", "").strip():
            raise ValueError("Human reviewer and review timestamp are required")
        datetime.fromisoformat(row["reviewed_at"])
        if row.get("source_sha256") != source_digest(source[key]):
            raise ValueError("Human label source fingerprint mismatch")
        tags = json.loads(row.get("human_tags") or "null")
        if (
            not isinstance(tags, list)
            or not all(isinstance(tag, str) for tag in tags)
            or len(tags) != len(set(tags))
            or set(tags) - TRAIT_KEYS
        ):
            raise ValueError("human_tags must explicitly list known trait keys; [] means none")
        truth[key] = set(tags)
    return truth


def confusion(predicted, actual, universe):
    tp, fp, fn = len(predicted & actual), len(predicted - actual), len(actual - predicted)
    return {
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "true_negative": len(universe - predicted - actual),
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall_in_sample": tp / (tp + fn) if tp + fn else None,
    }


def evaluate(rows, truth=None):
    if len(rows) != 100 or len({row["desertionNo"] for row in rows}) != 100:
        raise ValueError("Evaluation requires 100 distinct animals")
    universe = {row["desertionNo"] for row in rows}
    if truth is not None and set(truth) != universe:
        raise ValueError("Incomplete human truth")
    predictions = {row["desertionNo"]: match_candidates(normalized_values(row)) for row in rows}
    report = {
        "status": "evaluated_candidates" if truth is not None else "unmeasured_user_assumed_review",
        "generator": GENERATOR,
        "generator_version": VERSION,
        "sample_count": len(rows),
        "human_label_count": len(truth) if truth is not None else 0,
        "strata": dict(Counter(row["stratum"] for row in rows)),
        "candidate_counts": dict(
            Counter(key for ts in predictions.values() for key in {t.tag_key for t in ts})
        ),
        "release_enabled": sorted(RELEASED_RULE_IDS),
        "release_basis": RELEASE_BASIS,
        "human_precision_measured": truth is not None,
        "rule_observations": {
            rule.rule_id: {
                "tag_key": rule.tag_key,
                "prediction_count": sum(
                    any(t.rule_id == rule.rule_id for t in ts) for ts in predictions.values()
                ),
                "released": rule.rule_id in RELEASED_RULE_IDS,
            }
            for rule in RULES
        },
        "metrics": None,
        "limitations": [
            "100 disjoint sequential strata: behavior/health/admin-or-empty/random; not SRS.",
            "In-sample refinement is not independent validation or population recall.",
            "Per-rule FN measures that rule alone against all human positives for its tag.",
            "No prediction means precision is null, never 1.0. Confidence is not precision.",
        ],
    }
    if truth is None:
        return report
    by_tag, by_rule, cases = {}, {}, []
    for tag in sorted(TRAIT_KEYS):
        predicted = {key for key, ts in predictions.items() if any(t.tag_key == tag for t in ts)}
        actual = {key for key, ts in truth.items() if tag in ts}
        by_tag[tag] = confusion(predicted, actual, universe)
    for rule in RULES:
        predicted = {
            key for key, ts in predictions.items() if any(t.rule_id == rule.rule_id for t in ts)
        }
        actual = {key for key, ts in truth.items() if rule.tag_key in ts}
        metric = confusion(predicted, actual, universe)
        by_rule[rule.rule_id] = {
            "tag_key": rule.tag_key,
            **metric,
            # Evidence threshold is necessary, not automatic production approval.
            "eligible_for_release_review": metric["false_positive"] == 0
            and metric["true_positive"] >= MIN_TRUE_POSITIVES,
        }
    for index, row in enumerate(rows, 1):
        key = row["desertionNo"]
        predicted = {t.tag_key for t in predictions[key]}
        cases.append(
            {
                "sample_row": index,
                "false_positive": sorted(predicted - truth[key]),
                "false_negative": sorted(truth[key] - predicted),
                "false_positive_evidence": [
                    {"tag_key": t.tag_key, "rule_id": t.rule_id, "evidence": t.evidence}
                    for t in predictions[key]
                    if t.tag_key not in truth[key]
                ],
            }
        )
    total = {
        name: sum(m[name] for m in by_tag.values())
        for name in (
            "true_positive",
            "false_positive",
            "false_negative",
        )
    }
    tp, fp, fn = (total[name] for name in ("true_positive", "false_positive", "false_negative"))
    total.update(
        precision=tp / (tp + fp) if tp + fp else None,
        recall_in_sample=tp / (tp + fn) if tp + fn else None,
    )
    report["metrics"] = {"micro": total, "by_tag": by_tag, "by_rule": by_rule, "cases": cases}
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--sample", type=Path, required=True)
    parser.add_argument("--labels", type=Path)
    parser.add_argument("--export-labels", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        # Check destinations first; no accidental replacement of human source files.
        if args.output.exists() or (args.export_labels and args.export_labels.exists()):
            raise ValueError("Output already exists")
        rows = load_sample(args.raw, args.sample)
        truth = load_labels(args.labels, rows) if args.labels else None
        report = evaluate(rows, truth)
        report["input_sha256"] = {"raw": digest(args.raw), "sample": digest(args.sample)}
        if args.labels:
            report["input_sha256"]["labels"] = digest(args.labels)
        if args.export_labels:
            export_label_template(args.export_labels, rows)
        with args.output.open("x", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
        print(json.dumps({"status": report["status"], "sample_count": len(rows)}))
        return 0
    except (OSError, ValueError, KeyError, TypeError):
        print(json.dumps({"status": "failed", "error_code": "INVALID_BEHAVIOR_REVIEW_INPUT"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
