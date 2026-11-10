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


if __name__ == "__main__":
    unittest.main()
