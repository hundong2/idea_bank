import json
import tempfile
import unittest
from pathlib import Path

from krtax.maintenance import (
    MaintenanceError,
    SourceFingerprint,
    compare_fingerprints,
    load_source_registry,
    normalize_html,
    validate_project,
)


class MaintenanceHarnessTest(unittest.TestCase):
    def test_html_normalization_ignores_script_and_spacing(self):
        content = "<html><script>secret()</script><body> 종합   소득세 </body></html>".encode()
        self.assertEqual(normalize_html(content), "종합 소득세")

    def test_registry_blocks_non_official_host(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sources.json"
            path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "sources": [
                            {
                                "source_id": "bad",
                                "authority": "unknown",
                                "category": "policy",
                                "url": "https://example.com/policy",
                                "required_markers": ["tax"],
                                "review_cadence_days": 30,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(MaintenanceError):
                load_source_registry(path)

    def test_changed_fingerprint_is_reported(self):
        current = [
            SourceFingerprint("rate", "https://nts.go.kr/a", "https://nts.go.kr/a", "now", "new", None, None, 3)
        ]
        baseline = {"sources": {"rate": {"normalized_sha256": "old"}}}
        self.assertEqual(
            compare_fingerprints(current, baseline),
            [{"source_id": "rate", "status": "content_changed"}],
        )

    def test_project_validation(self):
        root = Path(__file__).resolve().parents[1]
        result = validate_project(root)
        self.assertEqual(result["status"], "ok")
        self.assertIn(2025, result["rulesets"])


if __name__ == "__main__":
    unittest.main()
