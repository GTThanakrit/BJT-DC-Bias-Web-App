import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from spice_engine import CEParams, build_netlist, validate_sim_params


def fixture_params() -> CEParams:
    return CEParams(
        vcc=12,
        r1=100000,
        r2=22000,
        rc=2200,
        re=1000,
        rl=10000,
        cin_uf=10,
        cout_uf=10,
        source_peak_v=0.01,
        source_freq_hz=1000,
        beta=100,
        vbe=0.7,
    )


def base_values() -> dict[str, str]:
    return {
        name: "1"
        for name in CEParams.__dataclass_fields__
        if name != "model_name"
    }


class ValidationTest(unittest.TestCase):
    def test_validate_rejects_zero_re(self):
        values = base_values()
        values.update(vcc="12", re="0", source_peak_v="0.01", source_freq_hz="1000", vbe="0.7")
        self.assertIn("re", validate_sim_params(values))

    def test_validate_rejects_bad_frequency(self):
        values = base_values()
        values.update(vcc="12", source_peak_v="0.01", source_freq_hz="0", vbe="0.7")
        self.assertIn("source_freq_hz", validate_sim_params(values))


class NetlistBuilderTest(unittest.TestCase):
    def test_build_netlist_dc_contains_op_and_model(self):
        with tempfile.TemporaryDirectory() as workdir:
            netlist = build_netlist("dc", fixture_params(), Path(workdir))
            text = netlist.read_text(encoding="utf-8")
        self.assertIn(".op", text)
        self.assertIn("CE_UNVERIFIED", text)
        self.assertIn(".print op v(vb) v(ve) v(vc) v(vc,ve) i(q1)", text)

    def test_build_netlist_ac_uses_vin_reference(self):
        with tempfile.TemporaryDirectory() as workdir:
            text = build_netlist("ac", fixture_params(), Path(workdir)).read_text(encoding="utf-8")
        self.assertIn(".ac dec 20 1 10Meg", text)
        self.assertIn(".print ac vdb(vout) vp(vout) vdb(vin) vp(vin)", text)

    def test_build_netlist_tran_encodes_amplitude_and_frequency(self):
        with tempfile.TemporaryDirectory() as workdir:
            text = build_netlist("tran", fixture_params(), Path(workdir)).read_text(encoding="utf-8")
        self.assertIn("SIN(0 0.01 1000)", text)
        self.assertIn(".tran 0 0.005 0 1e-05", text)


class RunnerTest(unittest.TestCase):
    def test_run_uses_argument_list_without_shell(self):
        seen = {}

        def fake_run(args, **kwargs):
            seen.update(args=args, kwargs=kwargs)
            return subprocess.CompletedProcess(args, 0, "ok", "")

        with tempfile.TemporaryDirectory() as workdir:
            path = Path(workdir)
            (path / "run.log").write_text("ok", encoding="utf-8")
            with patch("spice_engine.subprocess.run", side_effect=fake_run):
                from spice_engine import run_ngspice

                run_ngspice("dc", path / "dc.cir", path)
        self.assertIsInstance(seen["args"], list)
        self.assertEqual(seen["kwargs"]["cwd"], path)
        self.assertEqual(seen["kwargs"]["timeout"], 30)
        self.assertIsNot(seen["kwargs"].get("shell"), True)

    def test_run_returns_engine_unavailable_when_binary_missing(self):
        from spice_engine import run_ngspice

        with tempfile.TemporaryDirectory() as workdir:
            with patch("spice_engine.subprocess.run", side_effect=FileNotFoundError):
                result = run_ngspice("dc", Path(workdir) / "dc.cir", Path(workdir))
        self.assertFalse(result.ok)
        self.assertIn("ENGINE NOT AVAILABLE", result.error)

    def test_run_rejects_nonzero_exit(self):
        from spice_engine import run_ngspice

        with tempfile.TemporaryDirectory() as workdir:
            path = Path(workdir)
            (path / "run.log").write_text("Fatal error", encoding="utf-8")
            with patch(
                "spice_engine.subprocess.run",
                return_value=subprocess.CompletedProcess([], 1, "", "Fatal error"),
            ):
                result = run_ngspice("dc", path / "dc.cir", path)
        self.assertFalse(result.ok)
        self.assertIn("RUN FAILED", result.error)

    def test_run_rejects_empty_log(self):
        from spice_engine import run_ngspice

        with tempfile.TemporaryDirectory() as workdir:
            path = Path(workdir)
            (path / "run.log").write_text("", encoding="utf-8")
            with patch(
                "spice_engine.subprocess.run",
                return_value=subprocess.CompletedProcess([], 0, "", ""),
            ):
                result = run_ngspice("dc", path / "dc.cir", path)
        self.assertFalse(result.ok)
        self.assertIn("EMPTY OUTPUT", result.error)


if __name__ == "__main__":
    unittest.main()
