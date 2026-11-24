import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
