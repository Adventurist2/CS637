import json

import pytest

from sequin.cli import main


def test_priority_cli_exports_settings_and_service_metrics(tmp_path):
    assert main(["simulate", "--case", "14", "--sequence", "1,3", "--critical-buses", "12,14",
                 "--critical-first", "--output", str(tmp_path)]) == 0
    result = json.loads((tmp_path / "trace.json").read_text())
    assert result["settings"]["critical_first"] is True
    assert result["settings"]["critical_buses"] == "12,14"
    assert result["service_metrics"]["critical_demand_mw"] > 0
    assert "service_floor_tolerance_pu" in result["trace"][-1]


def test_benchmark_preserves_priority_response_policy(tmp_path):
    assert main(["benchmark", "--cases", "14", "--seeds", "0", "--ks", "1", "--methods", "greedy-flow",
                 "--critical-buses", "12,14", "--priority-weight", "10", "--output", str(tmp_path)]) == 0
    result = json.loads((tmp_path / "results.json").read_text())
    assert result["settings"]["priority_weight"] == 10
    assert result["results"][0]["critical_demand_mw"] > 0
    assert 0 <= result["results"][0]["critical_retained_fraction"] <= 1


def test_timing_cli_rejects_nonpositive_windows(tmp_path):
    with pytest.raises(SystemExit) as exc:
        main(["timing", "--case", "14", "--sequence", "1,3", "--durations-minutes", "0,15",
              "--output", str(tmp_path)])
    assert exc.value.code == 2
    assert not (tmp_path / "timing.json").exists()
