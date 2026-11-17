"""HTTP tests through Flask's test client."""

import unittest

from app import app


VALID_FORM = {
    "vcc": "12",
    "r1": "100000",
    "r2": "22000",
    "rc": "2200",
    "re": "1000",
    "beta": "100",
    "vbe": "0.7",
}

FIXED_FORM = {
    "mode": "fixed",
    "vcc": "12",
    "rb": "1000000",
    "rc": "2200",
    "beta": "100",
    "vbe": "0.7",
}

EMITTER_FORM = dict(FIXED_FORM, mode="emitter", re="1000")


class RouteTest(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def post(self, **overrides):
        form = dict(VALID_FORM)
        form.update({k: str(v) for k, v in overrides.items()})
        return self.client.post("/", data=form)

    def test_get_returns_form_with_defaults(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("BJT DC Bias Calculator", body)
        self.assertIn('name="vcc"', body)
        self.assertIn('value="100000"', body)
        self.assertIn("Calculate DC Bias", body)

    def test_post_computes_operating_point_server_side(self):
        response = self.post()

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Forward-Active", body)
        self.assertIn("9.294 V", body)   # VC
        self.assertIn("1.230 mA", body)  # IC
        self.assertIn("8.052 V", body)   # VCE

    def test_post_recomputes_for_a_different_circuit(self):
        """A hard-coded template would keep showing the reference numbers."""

        response = self.post(rc="8200")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("1.915 V", body)      # VC moves with RC
        self.assertNotIn("9.294 V", body)   # old VC must be gone
        self.assertIn("ใกล้ Saturation", body)

    def test_post_rejects_zero_resistance(self):
        response = self.post(r1="0")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("ต้องมากกว่า 0", body)
        self.assertNotIn('class="region region-', body)

    def test_post_rejects_non_numeric_input(self):
        response = self.post(vcc="abc")

        self.assertEqual(response.status_code, 200)
        self.assertIn("ต้องเป็นตัวเลข", response.get_data(as_text=True))

    def test_post_rejects_missing_field(self):
        form = dict(VALID_FORM)
        form.pop("r2")

        response = self.client.post("/", data=form)

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("กรุณากรอกค่านี้", body)
        self.assertNotIn('class="region region-', body)

    def test_post_reports_cutoff_region(self):
        response = self.post(r2="1000")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Cutoff", body)
        self.assertIn("ข้อจำกัดของแบบจำลอง", body)

    def test_post_marks_saturated_values_as_untrustworthy(self):
        response = self.post(r1="10000", r2="10000", rc="20000")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Saturation", body)
        self.assertIn("ห้ามนำไปใช้", body)
        self.assertIn('class="untrusted"', body)


class MultiModeRouteTest(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def post_form(self, form, **overrides):
        data = dict(form)
        data.update({k: str(v) for k, v in overrides.items()})
        return self.client.post("/", data=data)

    def test_fixed_mode_get_shows_only_its_fields(self):
        body = self.client.get("/?mode=fixed").get_data(as_text=True)

        self.assertIn('name="rb"', body)
        self.assertNotIn('name="r1"', body)

    def test_emitter_mode_get_shows_re_but_not_divider_fields(self):
        body = self.client.get("/?mode=emitter").get_data(as_text=True)

        self.assertIn('name="re"', body)
        self.assertNotIn('name="r1"', body)

    def test_mode_selector_marks_the_current_mode(self):
        divider = self.client.get("/").get_data(as_text=True)
        fixed = self.client.get("/?mode=fixed").get_data(as_text=True)

        self.assertIn('<select name="mode"', fixed)
        self.assertIn('value="divider" selected', divider)
        self.assertIn('value="fixed" selected', fixed)

    def test_post_form_carries_hidden_mode(self):
        body = self.post_form(FIXED_FORM).get_data(as_text=True)

        self.assertIn('type="hidden" name="mode"', body)

    def test_mode_selector_explains_that_submit_is_required(self):
        body = self.client.get("/?mode=fixed").get_data(as_text=True)

        self.assertIn("เพื่อเปลี่ยนช่องกรอก", body)
        self.assertIn("กดปุ่ม", body)

    def test_fixed_mode_post_computes_operating_point(self):
        body = self.post_form(FIXED_FORM).get_data(as_text=True)

        self.assertIn("9.514 V", body)   # VC = VCE for VE = 0
        self.assertIn("1.130 mA", body)  # IC

    def test_emitter_mode_post_computes_operating_point(self):
        body = self.post_form(EMITTER_FORM).get_data(as_text=True)

        self.assertIn("8.705 V", body)  # VCE

    def test_unknown_mode_is_rejected(self):
        body = self.post_form(FIXED_FORM, mode="bogus").get_data(as_text=True)

        self.assertIn("โหมดวงจรไม่ถูกต้อง", body)
        self.assertNotIn('class="region region-', body)

    def test_fixed_missing_rb_has_no_result(self):
        form = dict(FIXED_FORM)
        form.pop("rb")

        body = self.client.post("/", data=form).get_data(as_text=True)

        self.assertIn("กรุณากรอกค่านี้", body)
        self.assertNotIn('class="region region-', body)

    def test_fixed_zero_rb_has_no_result(self):
        body = self.post_form(FIXED_FORM, rb="0").get_data(as_text=True)

        self.assertIn("ต้องมากกว่า 0", body)
        self.assertNotIn('class="region region-', body)

    def test_invalid_input_does_not_show_stale_result(self):
        first = self.post_form(VALID_FORM).get_data(as_text=True)
        self.assertIn('class="region region-', first)

        body = self.post_form(VALID_FORM, vcc="abc").get_data(as_text=True)

        self.assertIn("ต้องเป็นตัวเลข", body)
        self.assertNotIn('class="region region-', body)


if __name__ == "__main__":
    unittest.main()
