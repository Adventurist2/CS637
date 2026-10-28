from pathlib import Path
import numpy as np
import pytest

from sequin import load_case


@pytest.mark.parametrize("name,shape", [("14", (14, 20, 5)), ("39", (39, 46, 10)),
    ("60", (60, 88, 23)), ("118", (118, 186, 54)), ("162", (162, 284, 12)), ("240", (240, 448, 143))])
def test_paper_benchmark_sizes(name, shape):
    case = load_case(name)
    assert (case.nbus, case.nbranch, case.ngen) == shape


def test_correct_stressed_case():
    assert load_case("14").total_demand_mw == pytest.approx(462.97)


def test_perturbation_is_paired_and_reproducible():
    case = load_case("39")
    a, b = case.scenario(5), case.scenario(5)
    assert np.array_equal(a.demand, b.demand)
    assert not np.array_equal(a.demand, case.scenario(6).demand)
    assert np.all(a.demand >= 0.95 * case.demand)
    assert np.all(a.demand <= 1.05 * case.demand)
    assert a.source_sha256 == case.source_sha256


def test_negative_load_preprocessing_is_disclosed():
    case = load_case("162")
    assert case.clipped_negative_load_mw == 0
    assert case.injections.sum() > 0
    assert np.all(case.demand >= 0)


def test_malformed_input_fails_clearly(tmp_path):
    path = tmp_path / "bad.m"
    path.write_text("mpc.baseMVA = 100;", encoding="utf-8")
    with pytest.raises(ValueError, match="Missing MATPOWER matrix"):
        load_case(path)
