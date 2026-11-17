"""Unit tests for the Lab 03 multi-bias engineering interface (no Flask).

Expected values are derived by hand from the forward-active equations in
docs/superpowers/specs/2026-11-17-lab03-multi-bias-design.md, independently
of the implementation.
"""

import unittest

from dc_bias import (
    COMMON_FIELDS,
    MODE_DIVIDER,
    MODE_EMITTER,
    MODE_FIXED,
    RESULT_KEYS,
    compute_divider_bias,
    compute_emitter_bias,
    compute_fixed_bias,
    fields_for_mode,
    validate_mode,
)

FIXED = {
    "vcc": 12.0,
    "rb": 1_000_000.0,
    "rc": 2_200.0,
    "beta": 100.0,
    "vbe": 0.70,
}

EMITTER_1K = {
    "vcc": 12.0,
    "rb": 1_000_000.0,
    "rc": 2_200.0,
    "re": 1_000.0,
    "beta": 100.0,
    "vbe": 0.70,
}

DIVIDER = {
    "vcc": 12.0,
    "r1": 100_000.0,
    "r2": 22_000.0,
    "rc": 2_200.0,
    "re": 1_000.0,
    "beta": 100.0,
    "vbe": 0.70,
}


class FixedBiasTest(unittest.TestCase):
    def test_fixed_bias_matches_hand_calculation(self):
        result = compute_fixed_bias(FIXED)

        self.assertAlmostEqual(result["ib_ua"], 11.300, places=3)
        self.assertAlmostEqual(result["ic_ma"], 1.130, places=3)
        self.assertAlmostEqual(result["ve_v"], 0.0, places=9)
        self.assertAlmostEqual(result["vb_v"], 0.700, places=3)
        self.assertAlmostEqual(result["vc_v"], 9.514, places=3)
        self.assertAlmostEqual(result["vce_v"], 9.514, places=3)


class EmitterBiasTest(unittest.TestCase):
    def test_emitter_bias_matches_hand_calculation(self):
        result = compute_emitter_bias(EMITTER_1K)

        self.assertAlmostEqual(result["ib_ua"], 10.2634, places=4)
        self.assertAlmostEqual(result["ic_ma"], 1.02634, places=5)
        self.assertAlmostEqual(result["ve_v"], 1.03660, places=5)
        self.assertAlmostEqual(result["vce_v"], 8.70545, places=5)

    def test_increasing_re_reduces_ic(self):
        emitter_2k = dict(EMITTER_1K, re=2_000.0)

        result_1k = compute_emitter_bias(EMITTER_1K)
        result_2k = compute_emitter_bias(emitter_2k)

        self.assertAlmostEqual(result_2k["ic_ma"], 0.94010, places=5)
        self.assertLess(result_2k["ic_ma"], result_1k["ic_ma"])


class DividerAdapterTest(unittest.TestCase):
    def test_divider_result_unchanged_and_shares_result_keys(self):
        result = compute_divider_bias(DIVIDER)

        self.assertAlmostEqual(result["ic_ma"], 1.22986, places=5)
        self.assertAlmostEqual(result["vce_v"], 8.05216, places=5)
        for key in RESULT_KEYS:
            self.assertIn(key, result)


class ModeHelpersTest(unittest.TestCase):
    def test_unknown_mode_has_no_fields(self):
        self.assertIsNone(fields_for_mode("bogus"))

    def test_known_modes_cover_common_fields(self):
        for mode in (MODE_DIVIDER, MODE_FIXED, MODE_EMITTER):
            fields = fields_for_mode(mode)
            self.assertIsNotNone(fields)
            for key in COMMON_FIELDS:
                self.assertIn(key, fields)

    def test_fixed_missing_rb_is_reported(self):
        values = {
            "vcc": 12.0,
            "rc": 2_200.0,
            "beta": 100.0,
            "vbe": 0.7,
        }

        errors = validate_mode(MODE_FIXED, values)

        self.assertIn("rb", errors)


if __name__ == "__main__":
    unittest.main()
