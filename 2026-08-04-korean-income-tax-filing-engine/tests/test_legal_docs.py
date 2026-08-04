import tomllib
import unittest
from pathlib import Path


class LegalDocumentationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]

    def test_package_declares_apache_license_file(self):
        with (self.root / "pyproject.toml").open("rb") as stream:
            project = tomllib.load(stream)["project"]
        self.assertEqual(project["license"], {"file": "LICENSE"})
        self.assertIn("License :: OSI Approved :: Apache Software License", project["classifiers"])

    def test_license_contains_unmodified_core_sections(self):
        license_text = (self.root / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("Apache License\n                           Version 2.0", license_text)
        self.assertIn("7. Disclaimer of Warranty.", license_text)
        self.assertIn("8. Limitation of Liability.", license_text)
        self.assertIn("9. Accepting Warranty or Additional Liability.", license_text)

    def test_disclaimer_and_contribution_controls_are_linked(self):
        readme = (self.root / "README.md").read_text(encoding="utf-8")
        disclaimer = (self.root / "DISCLAIMER.md").read_text(encoding="utf-8")
        contributing = (self.root / "CONTRIBUTING.md").read_text(encoding="utf-8")
        self.assertIn("Apache-2.0", readme)
        self.assertIn("세무·법률 자문", disclaimer)
        self.assertIn("AS IS", disclaimer)
        self.assertIn("Signed-off-by:", contributing)


if __name__ == "__main__":
    unittest.main()
