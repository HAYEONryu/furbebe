"""Synthetic source pages; no API key, network, or production tag dictionary fixtures."""

from copy import deepcopy

from backend.jobs.animal_sync.client import Page


def source_row(source_id="animal-1", **changes):
    return {
        "desertionNo": source_id,
        "upKindCd": "417000",
        "upKindNm": "개",
        "kindNm": "믹스견",
        "kindFullNm": "[개] 믹스견",
        "sexCd": "F",
        "neuterYn": "U",
        "age": "2025(년생)",
        "weight": "5(Kg)",
        "colorCd": "흰색",
        "processState": "보호중",
        "specialMark": "검토용 원문",
        "careRegNo": "shelter-1",
        "careNm": "검토용 보호소",
        "happenDt": "20260901",
        "noticeSdt": "20260901",
        "noticeEdt": "20260911",
        "updTm": "2026-09-14 12:00:00",
        "popfile1": "https://example.invalid/one.jpg",
        "popfile2": "https://example.invalid/two.jpg",
        **changes,
    }


class SnapshotClient:
    retries = 0

    def __init__(self, rows, *, fail_on=None, failure=None, total=None, clamp=None):
        self.rows = deepcopy(rows)
        self.calls = []
        self.attempts = 0
        self.fail_on, self.failure, self.total, self.clamp = fail_on, failure, total, clamp

    def fetch(self, page, size, *, filters=None):
        self.attempts += 1
        self.calls.append(page)
        if page == self.fail_on:
            raise self.failure
        effective = self.clamp or size
        rows = self.rows[(page - 1) * effective : page * effective]
        total = len(self.rows) if self.total is None else self.total
        return Page(page, total, rows, "array", {}, {}, effective)


def envelope(rows, *, page=1, size=1000, total=None, code="00"):
    return {
        "response": {
            "header": {"resultCode": code},
            "body": {
                "pageNo": page,
                "numOfRows": size,
                "totalCount": len(rows) if total is None else total,
                "items": {"item": rows},
            },
        }
    }
