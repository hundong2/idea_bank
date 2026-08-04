import unittest

from krtax.efile import FixedWidthField, FixedWidthSpec, render_fixed_width
from krtax.errors import EFileSpecUnavailable, ValidationError


class EFileTest(unittest.TestCase):
    def test_unreviewed_spec_is_rejected(self):
        with self.assertRaises(EFileSpecUnavailable):
            render_fixed_width([{"tax_year": 2025, "amount": 1}], None)

    def test_generic_reviewed_spec_renders_deterministically(self):
        spec = FixedWidthSpec(
            tax_year=2025,
            spec_id="TEST-ONLY",
            encoding="ascii",
            line_ending="\r\n",
            reviewed=True,
            fields=(
                FixedWidthField("kind", 2),
                FixedWidthField("amount", 5, kind="number"),
            ),
        )
        self.assertEqual(
            render_fixed_width([{"tax_year": 2025, "kind": "A", "amount": 12}], spec),
            b"A 00012\r\n",
        )

    def test_overflow_is_not_truncated(self):
        spec = FixedWidthSpec(
            tax_year=2025,
            spec_id="TEST-ONLY",
            encoding="ascii",
            line_ending="\n",
            reviewed=True,
            fields=(FixedWidthField("value", 2),),
        )
        with self.assertRaises(ValidationError):
            render_fixed_width([{"tax_year": 2025, "value": "TOO-LONG"}], spec)

    def test_tax_year_mismatch_is_rejected(self):
        spec = FixedWidthSpec(
            tax_year=2025,
            spec_id="TEST-ONLY",
            encoding="ascii",
            line_ending="\n",
            reviewed=True,
            fields=(FixedWidthField("value", 2),),
        )
        with self.assertRaises(ValidationError):
            render_fixed_width([{"tax_year": 2026, "value": "A"}], spec)


if __name__ == "__main__":
    unittest.main()
