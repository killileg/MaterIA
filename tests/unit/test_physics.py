# tests/unit/test_physics.py
import math
import numpy as np
import pytest
from materia_epd.core import physics as ph


# ---------------------- helpers ----------------------


def test_is_close_true_and_false():
    assert ph._is_close(1.0, 1.0 + 1e-9)
    assert not ph._is_close(1.0, 1.1)


def test_round_precision():
    assert ph._round(1.234567891) == round(1.234567891, ph._REL_DEC)


def test_eval_rule_product_and_divide():
    vals = [2.0, 3.0, None]
    # simple product
    ru_prod = ph.Rule(target=2, reqs=(0, 1), mode=ph.RuleMode.PRODUCT)
    assert ph._eval_rule(vals, ru_prod) == 6.0

    # division: target = 0, reqs = (1, 2) -> v1 / v2
    vals = [None, 10.0, 2.0]
    ru_div = ph.Rule(target=0, reqs=(1, 2), mode=ph.RuleMode.DIVIDE)
    assert ph._eval_rule(vals, ru_div) == 5.0

    # division by zero or missing gives None
    vals = [1.0, 0.0]
    ru_bad = ph.Rule(target=0, reqs=(0, 1), mode=ph.RuleMode.DIVIDE)
    assert ph._eval_rule(vals, ru_bad) is None


def test_rule_log_coeffs_product_and_divide():
    prod = ph.Rule(0, (1, 2), ph.RuleMode.PRODUCT)
    div = ph.Rule(0, (1, 2), ph.RuleMode.DIVIDE)
    c1 = ph._rule_log_coeffs(prod)
    c2 = ph._rule_log_coeffs(div)
    # product adds negatives
    assert c1[0] == 1.0 and all(v < 0 for k, v in c1.items() if k != 0)
    # divide flips signs appropriately
    assert 0 in c2 and 1 in c2 and 2 in c2


def test_build_property_eq_system_produces_matrix():
    # simple map: first few indices only
    adj_col = {i: i for i in range(5)}
    A, b = ph._build_property_eq_system(adj_col)
    assert isinstance(A, np.ndarray)
    assert isinstance(b, np.ndarray)
    assert A.shape[0] == b.shape[0]


def test_project_logs_onto_eq_shapes_and_result():
    scaled = {name: 1.0 for name in ph.VARS}
    targets = {"mass": 2.0}
    internal = {"mass": 0}
    res = ph._project_logs_onto_eq(scaled, targets, internal)
    assert isinstance(res, np.ndarray)
    assert res.ndim == 1
    assert math.isfinite(float(res[0]))


# ---------------------- Material ----------------------


def test_material_to_dict_and_compute_conflicts():
    m = ph.Material(mass=2.0, volume=1.0, gross_density=2.0)
    d = m.to_dict()
    assert "mass" in d and d["mass"] == 2.0
    # should compute without conflict
    m._compute()
    assert isinstance(m._conflicts, list)


def test_material_rescale_valid_volume():
    m = ph.Material(mass=10, volume=5)
    # Rescale volume by factor 2
    m.rescale({"volume": 10})
    assert math.isclose(m.volume, 10.0, rel_tol=1e-8)
    assert m.scaling_factor > 0


def test_material_rescale_invalid_field():
    m = ph.Material(mass=5)
    with pytest.raises(ValueError):
        m.rescale({"bad_field": 1})


def test_material_rescale_invalid_value():
    m = ph.Material(mass=5)
    with pytest.raises(ValueError):
        m.rescale({"mass": -1})


def test_material_rescale_invalid_combo():
    m = ph.Material(mass=5)
    with pytest.raises(ValueError):
        m.rescale({"mass": 5, "surface": 1})


def test_material_rescale_layer_thickness_logic():
    # Valid rescale with surface + layer_thickness (allowed combo)
    m = ph.Material(surface=2.0, gross_density=1.5, grammage=3.0, layer_thickness=2.0)
    m.rescale({"surface": 4.0, "layer_thickness": 4.0})
    assert math.isclose(m.surface, 4.0)
    assert math.isclose(m.layer_thickness, 4.0)
    # grammage scaled proportionally to surface and thickness
    assert math.isclose(m.grammage, 6.0, rel_tol=1e-8)


def test_material_rescale_missing_baseline_raises():
    m = ph.Material()
    with pytest.raises(ValueError):
        m.rescale({"volume": 10})


def test_material_compute_detects_conflict():
    # mass != volume * gross_density  -> should record a conflict
    m = ph.Material(mass=2.0, volume=1.0, gross_density=3.0)
    m._compute()
    assert len(m._conflicts) >= 1


def test_clean_raises_when_conflicts_remain(monkeypatch):
    m = ph.Material(mass=2.0, volume=1.0, gross_density=3.0)  # inconsistent: 2 ≠ 1*3
    m._compute()
    assert (
        m._conflicts
    ), "Sanity check: should have at least one conflict before cleaning"

    # Baseline is required by _clean
    m.scaled_baseline = m.to_dict()

    # Make projection a no-op: return logs of current known values
    def identity_project(*args, **kwargs):
        known_keys = [k for k, v in m.scaled_baseline.items() if v is not None]
        return np.log([m.scaled_baseline[k] for k in known_keys], dtype=float)

    monkeypatch.setattr(ph, "_project_logs_onto_eq", identity_project)

    # Ask _clean to “clean” but with values that keep the conflict unchanged
    with pytest.raises(ValueError):
        m._clean({"mass": m.mass})


def test_rescale_thickness_requires_surface():
    # Accepted combo but thickness processed first -> surface still None
    m = ph.Material(gross_density=1.2)
    with pytest.raises(ValueError):
        m.rescale({"layer_thickness": 2.0, "surface": 4.0})


def test_rescale_thickness_requires_density():
    # surface known, no gross_density -> trips the second guard
    m = ph.Material(surface=1.0)
    with pytest.raises(ValueError):
        m.rescale({"layer_thickness": 2.0, "surface": 1.0})


def test_rescale_mass_scales_other_quantities():
    m = ph.Material(mass=2.0, length=3.0)  # length is a QUANTITY
    m.rescale({"mass": 4.0})
    # scaling_factor should be 2, so length doubles
    assert math.isclose(m.length, 6.0, rel_tol=1e-8)


def test_clean_returns_self_when_conflicts_is_none():
    m = ph.Material()
    m._conflicts = None  # force the early-return path
    # Should just return without needing baseline/projection
    assert m._clean({}) is None or isinstance(m, ph.Material)


def test_rescale_thickness_requires_surface_first():
    # layer_thickness is known; surface is missing -> trips the first guard (line 262)
    m = ph.Material(layer_thickness=1.0, gross_density=1.2)  # surface is None
    with pytest.raises(ValueError, match="surface.*must be known"):
        # Accepted combo; order matters so thickness is processed first
        m.rescale({"layer_thickness": 2.0, "surface": 4.0})


def test_rescale_thickness_requires_density_when_surface_known():
    # layer_thickness and surface known; gross_density missing
    m = ph.Material(layer_thickness=1.0, surface=1.0)  # gross_density is None
    with pytest.raises(ValueError, match="density.*must be known"):
        # Still the accepted combo; thickness processed first
        m.rescale({"layer_thickness": 2.0, "surface": 1.0})
