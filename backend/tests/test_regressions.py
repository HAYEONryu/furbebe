"""Regression tests for observed defects and high-impact collection guards."""

from datetime import date
from pathlib import Path

import pytest

from backend.jobs.animal_sync.client import Redactor
from backend.jobs.animal_sync.field_stats import parse_age, parse_weight, profile_dates
from backend.jobs.animal_sync.metrics import number_profile
from backend.jobs.animal_sync.profiling import main
from backend.jobs.animal_sync.source_models import normalize_items


def test_empty_array_items_container():
    assert normalize_items({"items": []}) == ([], "items_empty")


@pytest.mark.parametrize(("field", "parser"), [("weight", parse_weight), ("age", parse_age)])
def test_nonstring_source_numbers_count_as_failures(field, parser):
    result = number_profile([{field: 7}, {field: None}, {field: "."}], field, parser, Redactor())
    assert result["denominator_nonplaceholder"] == 1
    assert result["parse_failure"] == 1


def test_invalid_calendar_separate_from_unsupported_format():
    result = profile_dates(
        [{"happenDt": "20260229"}, {"happenDt": "unknown format"}, {"happenDt": 20260911}],
        date(2026, 9, 11),
    )
    assert result["happenDt"]["invalid_calendar_dates"] == 1
    assert result["happenDt"]["parse_failure"] == 3


def test_bounded_query_cannot_claim_entire_population():
    with pytest.raises(SystemExit) as caught:
        main(
            ["--start-date", "20260101", "--end-date", "20260911", "--entire-population-confirmed"]
        )
    assert caught.value.code == 2


def test_pending_config_does_not_call_api(tmp_path, monkeypatch, capsys):
    import backend.jobs.animal_sync.profiling as cli

    monkeypatch.setattr(cli, "ROOT", Path(tmp_path))
    monkeypatch.delenv("DATA_GO_KR_SERVICE_KEY", raising=False)
    assert cli.main(["--check-config"]) == 2
    assert "false" in capsys.readouterr().out
