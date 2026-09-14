import csv

import pytest

from backend.jobs.animal_sync.client import ApiFailure, Redactor, load_service_key
from backend.jobs.animal_sync.evidence import export_review


def test_replay_preserves_human_review_notes(tmp_path):
    path = tmp_path / "review.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, ["desertionNo", "review_notes"])
        writer.writeheader()
        writer.writerow({"desertionNo": "001", "review_notes": "Human-reviewed: ambiguous context"})
    before = path.read_bytes()
    with pytest.raises(ApiFailure, match="MANUAL_REVIEW_NOTES_EXIST"):
        export_review(path, [], Redactor())
    assert path.read_bytes() == before


def test_dotenv_utf8_bom(tmp_path, monkeypatch):
    monkeypatch.delenv("DATA_GO_KR_SERVICE_KEY", raising=False)
    (tmp_path / ".env").write_text("DATA_GO_KR_SERVICE_KEY=FAKE_BOM_KEY\n", encoding="utf-8-sig")
    assert load_service_key(tmp_path) == "FAKE_BOM_KEY"
