import unittest
from pathlib import Path


class ToolchainTest(unittest.TestCase):
    def test_generic_model_file_is_labelled_unverified(self):
        text = Path("spice_models/ce_generic.mod").read_text(encoding="utf-8")
        self.assertIn(".model CE_UNVERIFIED NPN", text)
        self.assertIn("UNVERIFIED", text)


if __name__ == "__main__":
    unittest.main()
