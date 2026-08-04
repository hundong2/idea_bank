import unittest

from krtax import (
    ExpenseMethod,
    FreelanceIncome,
    IncomeProfile,
    TaxCase,
    UnsupportedCase,
    ValidationError,
    WageIncome,
    calculate,
)


class CalculatorTest(unittest.TestCase):
    def test_wage_deduction_boundaries(self):
        cases = [
            (5_000_000, 3_500_000),
            (15_000_000, 7_500_000),
            (45_000_000, 12_000_000),
            (100_000_000, 14_750_000),
            (500_000_000, 20_000_000),
        ]
        for gross, deduction in cases:
            with self.subTest(gross=gross):
                result = calculate(TaxCase(tax_year=2025, wage=WageIncome(gross_pay=gross)))
                self.assertEqual(result.wage_income_deduction, deduction)

    def test_mixed_income_and_withholding_are_combined(self):
        result = calculate(
            TaxCase(
                tax_year=2025,
                wage=WageIncome(50_000_000, withheld_income_tax=1_000_000),
                freelance=FreelanceIncome(
                    10_000_000,
                    withheld_income_tax=300_000,
                    withheld_local_income_tax=30_000,
                    expense_method=ExpenseMethod.SIMPLE_RATE,
                    simple_expense_rate_bps=6000,
                    simple_rate_eligibility_confirmed=True,
                    industry_code="TEST-CODE",
                ),
                income_deductions=1_500_000,
            )
        )
        self.assertEqual(result.profile, IncomeProfile.MIXED)
        self.assertEqual(result.business_income_amount, 4_000_000)
        self.assertEqual(result.prepaid_income_tax, 1_300_000)
        self.assertEqual(result.withheld_local_income_tax, 30_000)

    def test_tax_rate_example_from_nts(self):
        result = calculate(
            TaxCase(
                tax_year=2025,
                freelance=FreelanceIncome(
                    gross_receipts=30_000_000,
                    expense_method=ExpenseMethod.FINALIZED_INCOME,
                    finalized_business_income=30_000_000,
                ),
            )
        )
        self.assertEqual(result.calculated_income_tax, 3_240_000)

    def test_simple_rate_requires_explicit_eligibility(self):
        with self.assertRaises(ValidationError):
            FreelanceIncome(
                gross_receipts=10_000_000,
                expense_method=ExpenseMethod.SIMPLE_RATE,
                simple_expense_rate_bps=6000,
                industry_code="940909",
            )

    def test_unsupported_year_fails_closed(self):
        with self.assertRaises(UnsupportedCase):
            calculate(TaxCase(tax_year=2026, wage=WageIncome(10_000_000)))

    def test_complex_income_fails_closed(self):
        with self.assertRaises(UnsupportedCase):
            calculate(TaxCase(tax_year=2025, wage=WageIncome(10_000_000), has_other_income=True))

    def test_business_loss_fails_closed(self):
        case = TaxCase(
            tax_year=2025,
            freelance=FreelanceIncome(
                gross_receipts=1_000_000,
                expense_method=ExpenseMethod.ACTUAL,
                actual_expenses=1_000_001,
            ),
        )
        with self.assertRaises(UnsupportedCase):
            calculate(case)


if __name__ == "__main__":
    unittest.main()
