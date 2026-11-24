import unittest

from plots import bode_svg, waveform_svg


class BodeSvgTest(unittest.TestCase):
    def test_bode_svg_has_units_and_changes_with_data(self):
        base = bode_svg([1, 10], [0, -10], [-180, -190])
        changed = bode_svg([1, 10], [20, -10], [-180, -190])
        self.assertIn("<svg", base)
        self.assertIn("Frequency (Hz)", base)
        self.assertIn("Gain (dB)", base)
        self.assertIn("Phase (deg)", base)
        self.assertNotEqual(base, changed)


class WaveformSvgTest(unittest.TestCase):
    def test_waveform_svg_has_units_traces_and_changes_with_amplitude(self):
        base = waveform_svg([0, 0.001], [0.01, -0.01], [-0.1, 0.1])
        changed = waveform_svg([0, 0.001], [0.02, -0.02], [-0.1, 0.1])
        self.assertIn("Time (ms)", base)
        self.assertIn("Voltage (V)", base)
        self.assertIn("Vin", base)
        self.assertIn("Vout", base)
        self.assertNotEqual(base, changed)


if __name__ == "__main__":
    unittest.main()
