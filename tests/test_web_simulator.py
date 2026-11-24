import unittest
from unittest.mock import patch

from app import app
from spice_engine import OpResult, SimulationResult


def valid_sim_data() -> dict[str, str]:
    return {
        "analysis": "dc",
        "vcc": "12",
        "r1": "100000",
        "r2": "22000",
        "rc": "2200",
        "re": "1000",
        "rl": "10000",
        "cin_uf": "10",
        "cout_uf": "10",
        "source_peak_v": "0.01",
        "source_freq_hz": "1000",
        "beta": "100",
        "vbe": "0.7",
        "model_name": "CE_UNVERIFIED",
    }


class SimulatorRouteTest(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_index_still_renders_lab03_with_simulator_link(self):
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn("BJT DC Bias Calculator", html)
        self.assertIn('href="/simulator"', html)

    def test_get_simulator_shows_defaults_and_no_results(self):
        html = self.client.get("/simulator").get_data(as_text=True)
        self.assertIn("CE Amplifier", html)
        self.assertNotIn("<svg", html)
        self.assertIn('name="source_freq_hz"', html)

    def test_post_simulate_invalid_re_shows_error_and_no_plot(self):
        data = valid_sim_data()
        data["re"] = "0"
        html = self.client.post("/simulate", data=data).get_data(as_text=True)
        self.assertIn("RE", html)
        self.assertIn("ต้องมากกว่า 0", html)
        self.assertNotIn("<svg", html)

    def test_post_simulate_success_shows_provenance_and_svg(self):
        fake = SimulationResult(
            "dc", True, "SUCCESS", "",
            OpResult(2.16, 1.50, 9.71, 8.21, 1.50),
            None, None,
            {"engine": "ngspice 47", "model": "CE_UNVERIFIED"},
        )
        with patch("app.simulate", return_value=fake):
            html = self.client.post("/simulate", data=valid_sim_data()).get_data(as_text=True)
        self.assertIn("ngspice 47", html)
        self.assertIn("UNVERIFIED", html)
        self.assertIn("<table", html)

    def test_post_simulate_engine_error_shows_status_and_no_plot(self):
        fake = SimulationResult(
            "dc", False, "ENGINE NOT AVAILABLE", "ngspice ไม่พบ",
            None, None, None, {"engine": "not available"},
        )
        with patch("app.simulate", return_value=fake):
            html = self.client.post("/simulate", data=valid_sim_data()).get_data(as_text=True)
        self.assertIn("ENGINE NOT AVAILABLE", html)
        self.assertNotIn("<svg", html)


if __name__ == "__main__":
    unittest.main()
