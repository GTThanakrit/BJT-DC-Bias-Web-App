import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from spice_engine import (
    CEParams,
    RunResult,
    build_netlist,
    parse_ac,
    parse_op,
    parse_tran,
    simulate,
    validate_sim_params,
)


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


OP_FIXTURE = "vb ve vc v(vc,ve) i(q1)\n2.16 1.50 9.71 8.21 1.50e-3\n"
AC_FIXTURE = (
    "freq vdb(vout) vp(vout) vdb(vin) vp(vin)\n"
    "1.000e+00 -20.0 -170.0 -60.0 -180.0\n"
    "1.000e+01 -40.0 -180.0 -60.0 -180.0\n"
)
TRAN_FIXTURE = (
    "time v(vin) v(vout)\n"
    "0.000e+00 0.010 -0.100\n"
    "1.000e-04 -0.010 0.100\n"
)


class ParserTest(unittest.TestCase):
    def test_parse_op_reads_columns_and_units(self):
        op = parse_op(OP_FIXTURE)
        self.assertAlmostEqual(op.vb_v, 2.16, places=2)
        self.assertAlmostEqual(op.ic_ma, 1.50, places=2)

    def test_parse_ac_computes_gain_relative_to_vin(self):
        ac = parse_ac(AC_FIXTURE)
        self.assertEqual(round(ac.gain_db[0]), 40)
        self.assertEqual(round(ac.phase_deg[0]), 10)

    def test_parse_ac_reports_cutoff_not_determined_when_no_crossing(self):
        self.assertIsNone(parse_ac(AC_FIXTURE).cutoff_hz)

    def test_parse_tran_detects_inversion(self):
        self.assertEqual(parse_tran(TRAN_FIXTURE).phase_relation, "inverted")

    def test_simulate_returns_parse_failed_on_bad_columns(self):
        with patch(
            "spice_engine.run_ngspice",
            return_value=RunResult(True, "nonsense", None, "47", ""),
        ):
            result = simulate("dc", fixture_params())
        self.assertFalse(result.ok)
        self.assertEqual(result.status, "PARSE FAILED")
        self.assertIsNone(result.op)


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
