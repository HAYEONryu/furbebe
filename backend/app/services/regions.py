"""Versioned official organization lookup. No address inference or network at request time."""

import json
from functools import lru_cache
from pathlib import Path


@lru_cache
def region_catalog():
    data = json.loads(
        (Path(__file__).resolve().parents[1] / "data" / "regions.json").read_text(encoding="utf-8")
    )
    return {row["organization"]: row for row in data["regions"]}


def region_for(organization):
    return region_catalog().get(organization)


def matching_organizations(*, sido=None, sigungu=None):
    return [
        name
        for name, row in region_catalog().items()
        if (sido is None or row["sido_code"] == sido)
        and (sigungu is None or row["sigungu_code"] == sigungu)
    ]
