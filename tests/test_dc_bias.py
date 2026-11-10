"""Unit tests for the engineering module (no Flask involved)."""

import unittest

from dc_bias import (
    REGION_ACTIVE,
    REGION_CUTOFF,
    REGION_SATURATION,
    WARNING_CUTOFF,
    WARNING_NEAR_CUTOFF,
    WARNING_NEAR_SATURATION,
    WARNING_SATURATION,
    DcBiasInputs,
    compute_dc_bias,
    validate_inputs,
)

# Lab 02 reference circuit: VCC=12 V, R1=100k, R2=22k, RC=2.2k, RE=1k,
# beta=100, VBE=0.70 V. Expected values were derived by hand from the
# Thevenin equations, independently of this implementation.
REFERENCE = DcBiasInputs(
    vcc=12.0,
    r1=100_000.0,
    r2=22_000.0,
    rc=2_200.0,
    re=1_000.0,
    beta=100.0,
    vbe=0.70,
)

# Second, independent circuit (different VCC, resistors, beta) so the physics
# is pinned by hand calculation in more than one place.
SECOND = DcBiasInputs(
    vcc=15.0,
    r1=47_000.0,
    r2=10_000.0,
    rc=3_300.0,
    re=1_000.0,
    beta=150.0,
    vbe=0.70,
)


class ReferenceCaseTest(unittest.TestCase):
    def test_operating_point_matches_hand_calculation(self):
        result = compute_dc_bias(REFERENCE)

        self.assertAlmostEqual(result.vth, 2.163934, places=6)
        self.assertAlmostEqual(result.rth, 18_032.786885, places=4)
        self.assertAlmostEqual(result.ib * 1e6, 12.298583, places=5)
        self.assertAlmostEqual(result.ic * 1e3, 1.229858, places=6)
        self.assertAlmostEqual(result.ie * 1e3, 1.242157, places=6)
        self.assertAlmostEqual(result.ve, 1.242157, places=6)
        self.assertAlmostEqual(result.vb, 1.942157, places=6)
        self.assertAlmostEqual(result.vc, 9.294312, places=6)
        self.assertAlmostEqual(result.vce, 8.052155, places=6)
        self.assertEqual(result.region, REGION_ACTIVE)
        self.assertIsNone(result.warning)

    def test_second_circuit_matches_hand_calculation(self):
        result = compute_dc_bias(SECOND)

        self.assertAlmostEqual(result.vth, 2.631579, places=6)
        self.assertAlmostEqual(result.rth, 8_245.614035, places=4)
        self.assertAlmostEqual(result.ib * 1e6, 12.129558, places=6)
        self.assertAlmostEqual(result.ic * 1e3, 1.819434, places=6)
        self.assertAlmostEqual(result.ie * 1e3, 1.831563, places=6)
        self.assertAlmostEqual(result.ve, 1.831563, places=6)
        self.assertAlmostEqual(result.vb, 2.531563, places=6)
        self.assertAlmostEqual(result.vc, 8.995869, places=6)
        self.assertAlmostEqual(result.vce, 7.164305, places=6)
        self.assertEqual(result.region, REGION_ACTIVE)

    def test_currents_obey_kirchhoff_and_ohms_law(self):
        result = compute_dc_bias(REFERENCE)

        self.assertAlmostEqual(result.ie, result.ib + result.ic, places=12)
        self.assertAlmostEqual(result.ve, result.ie * REFERENCE.re, places=9)
        self.assertAlmostEqual(result.vb, result.ve + REFERENCE.vbe, places=12)
        self.assertAlmostEqual(result.vce, result.vc - result.ve, places=12)
        self.assertAlmostEqual(
            result.vc, REFERENCE.vcc - result.ic * REFERENCE.rc, places=12
        )


class RegionWarningTest(unittest.TestCase):
    def test_cutoff_when_thevenin_voltage_below_vbe(self):
        params = DcBiasInputs(
            vcc=12.0, r1=100_000.0, r2=1_000.0, rc=2_200.0,
            re=1_000.0, beta=100.0, vbe=0.70,
        )
        result = compute_dc_bias(params)

        self.assertEqual(result.region, REGION_CUTOFF)
        self.assertEqual(result.warning, WARNING_CUTOFF)
        self.assertEqual(result.ic, 0.0)
        self.assertEqual(result.ve, 0.0)
        self.assertAlmostEqual(result.vce, 12.0, places=9)

    def test_vth_equal_to_vbe_is_cutoff(self):
        # VTH = 12 * 500 / (7500 + 500) = 0.75 V, exactly VBE.
        params = DcBiasInputs(
            vcc=12.0, r1=7_500.0, r2=500.0, rc=2_200.0,
            re=1_000.0, beta=100.0, vbe=0.75,
        )
        result = compute_dc_bias(params)

        self.assertEqual(result.region, REGION_CUTOFF)
        self.assertEqual(result.warning, WARNING_CUTOFF)

    def test_saturation_when_vce_falls_below_model_limit(self):
        params = DcBiasInputs(
            vcc=12.0, r1=10_000.0, r2=10_000.0, rc=20_000.0,
            re=1_000.0, beta=100.0, vbe=0.70,
        )
        result = compute_dc_bias(params)

        self.assertLessEqual(result.vce, 0.0)
        self.assertEqual(result.region, REGION_SATURATION)
        self.assertEqual(result.warning, WARNING_SATURATION)

    def test_near_saturation_keeps_active_region_but_warns(self):
        params = DcBiasInputs(
            vcc=12.0, r1=100_000.0, r2=22_000.0, rc=8_200.0,
            re=1_000.0, beta=100.0, vbe=0.70,
        )
        result = compute_dc_bias(params)

        self.assertEqual(result.region, REGION_ACTIVE)
        self.assertLess(result.vce, 1.0)
        self.assertEqual(result.warning, WARNING_NEAR_SATURATION)

    def test_barely_above_cutoff_warns_even_though_region_is_active(self):
        # VTH = 12 * 6242 / 106242 = 0.70502 V, only 5 mV above VBE.
        params = DcBiasInputs(
            vcc=12.0, r1=100_000.0, r2=6_242.0, rc=2_200.0,
            re=1_000.0, beta=100.0, vbe=0.70,
        )
        result = compute_dc_bias(params)

        self.assertEqual(result.region, REGION_ACTIVE)
        self.assertEqual(result.warning, WARNING_NEAR_CUTOFF)


class ValidationTest(unittest.TestCase):
    def _valid_values(self):
        return {
            "vcc": 12.0, "r1": 100_000.0, "r2": 22_000.0, "rc": 2_200.0,
            "re": 1_000.0, "beta": 100.0, "vbe": 0.70,
        }

    def test_accepts_reference_circuit(self):
        self.assertEqual(validate_inputs(self._valid_values()), {})

    def test_rejects_zero_or_negative_resistance(self):
        values = self._valid_values()
        values["r1"] = 0.0
        values["re"] = -5.0

        errors = validate_inputs(values)

        self.assertIn("r1", errors)
        self.assertIn("re", errors)

    def test_rejects_non_positive_beta_and_vcc(self):
        values = self._valid_values()
        values["beta"] = 0.0
        values["vcc"] = -1.0

        errors = validate_inputs(values)

        self.assertIn("beta", errors)
        self.assertIn("vcc", errors)

    def test_rejects_vbe_not_below_vcc(self):
        values = self._valid_values()
        values["vbe"] = 12.0

        self.assertIn("vbe", validate_inputs(values))

    def test_rejects_non_finite_values(self):
        for bad in (float("nan"), float("inf"), 1e300):
            values = self._valid_values()
            values["r1"] = bad
            self.assertIn("r1", validate_inputs(values), msg=f"value={bad}")


if __name__ == "__main__":
    unittest.main()
