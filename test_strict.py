"""
test_strict.py — Quality gate for the Atlas Bank Life Admin Assistant demo.

Every test here must pass before the app is considered demo-ready. Run
directly with `python3 test_strict.py` for a verbose PASS/FAIL summary
and a non-zero exit code on any failure.
"""

import copy
import re
import sys
import unittest
from datetime import date, timedelta

from bank_policies import ATLAS_POLICIES
from life_event_triggers import LifeEventScanner
from mock_data import (
    COST_OF_LIVING,
    CREDIT_PROFILE,
    CUSTOMER_PROFILE,
    FINANCIAL_GOALS,
    FINANCIAL_PRODUCTS,
    MONTHLY_SUMMARY,
    NOTIFICATION_PREFERENCES,
    SHOPPING_HABITS,
    TAX_REFERENCE,
    TODAY,
    TRANSACTIONS,
)
from system_prompt import build_system_prompt

REQUIRED_TRIGGER_SCHEMA_KEYS = {"event_type", "confidence", "evidence", "suggested_context"}


# ===========================================================================
class TestMockDataIntegrity(unittest.TestCase):
    """Verify the mock data is internally consistent and complete."""

    def test_customer_profile_completeness(self):
        required_fields = [
            "name", "age", "date_of_birth", "marital_status", "dependents",
            "education", "employment_history", "prior_city", "current_city",
            "phone", "email", "member_since",
        ]
        for field in required_fields:
            self.assertIn(field, CUSTOMER_PROFILE, f"Missing field: {field}")
            value = CUSTOMER_PROFILE[field]
            if isinstance(value, (list, dict)):
                self.assertTrue(len(value) > 0, f"Field is empty: {field}")
            elif isinstance(value, str):
                self.assertTrue(value.strip(), f"Field is empty: {field}")
            else:
                self.assertIsNotNone(value, f"Field is None: {field}")

    def test_employment_history_has_prior_and_current(self):
        history = CUSTOMER_PROFILE["employment_history"]
        self.assertGreaterEqual(len(history), 2)
        current = [job for job in history if job.get("end_date") is None]
        prior = [job for job in history if job.get("end_date") is not None]
        self.assertEqual(len(current), 1, "Expected exactly one current job")
        self.assertGreaterEqual(len(prior), 1, "Expected at least one prior job")

    def test_employment_history_excludes_salary(self):
        # Salary is confidential and must never be stored on the profile or
        # surfaced anywhere — income is inferred from actual deposits instead.
        for job in CUSTOMER_PROFILE["employment_history"]:
            self.assertNotIn("salary", job)

    def test_financial_products_completeness(self):
        self.assertIn("checking", FINANCIAL_PRODUCTS)
        self.assertIn("savings", FINANCIAL_PRODUCTS)
        self.assertIn("credit_card", FINANCIAL_PRODUCTS)
        self.assertIn("student_loans", FINANCIAL_PRODUCTS)

        for field in ("account_number_masked", "balance"):
            self.assertIn(field, FINANCIAL_PRODUCTS["checking"])

        for field in ("account_number_masked", "balance", "monthly_auto_transfer"):
            self.assertIn(field, FINANCIAL_PRODUCTS["savings"])

        for field in (
            "account_number_masked", "credit_limit", "current_balance", "apr",
            "minimum_payment", "payment_due_date", "rewards_type",
        ):
            self.assertIn(field, FINANCIAL_PRODUCTS["credit_card"])

        for field in (
            "servicer", "original_balance", "remaining_balance", "interest_rate",
            "monthly_payment", "expected_payoff_date",
        ):
            self.assertIn(field, FINANCIAL_PRODUCTS["student_loans"])

    def test_credit_profile_has_score_and_factors(self):
        self.assertIsInstance(CREDIT_PROFILE["score"], int)
        self.assertTrue(300 <= CREDIT_PROFILE["score"] <= 850)
        self.assertIsInstance(CREDIT_PROFILE["score_range"], str)
        self.assertTrue(CREDIT_PROFILE["score_range"])
        self.assertTrue(len(CREDIT_PROFILE["factors_helping"]) > 0)
        self.assertTrue(len(CREDIT_PROFILE["factors_hurting"]) > 0)

    def test_financial_goals_nonempty(self):
        self.assertGreaterEqual(len(FINANCIAL_GOALS), 2)

    def test_transactions_count(self):
        self.assertGreaterEqual(len(TRANSACTIONS), 60)

    def test_transactions_have_required_fields(self):
        required_fields = {"date", "description", "amount", "category", "merchant_type"}
        for txn in TRANSACTIONS:
            self.assertTrue(required_fields.issubset(txn.keys()), f"Missing fields in {txn}")

    def test_transactions_are_chronologically_sorted(self):
        dates = [txn["date"] for txn in TRANSACTIONS]
        self.assertEqual(dates, sorted(dates))

    def test_transactions_contain_life_event_signals(self):
        moving_txns = [t for t in TRANSACTIONS if t["category"] == "moving"]
        self.assertTrue(len(moving_txns) >= 1, "No moving-category transaction found")

        current_employer = CUSTOMER_PROFILE["employment_history"][-1]["employer"]
        new_employer_txns = [
            t for t in TRANSACTIONS
            if current_employer.upper() in t["description"].upper()
        ]
        self.assertTrue(len(new_employer_txns) >= 1, "No transaction references the new employer")

        deposit_txns = [
            t for t in TRANSACTIONS
            if "DEPOSIT" in t["description"].upper() or t["merchant_type"] == "property_management"
        ]
        self.assertTrue(len(deposit_txns) >= 1, "No security-deposit-like transaction found")

    def test_prior_rent_payments_stopped(self):
        rent_txns = sorted(
            [t for t in TRANSACTIONS if t["merchant_type"] == "landlord"],
            key=lambda t: t["date"],
        )
        self.assertTrue(len(rent_txns) >= 1, "No historical rent payments found")

        cutoff = (TODAY - timedelta(days=28)).isoformat()
        recent_rent = [t for t in rent_txns if t["date"] >= cutoff]
        self.assertEqual(len(recent_rent), 0, "Rent payment found within the last 4 weeks")

    def test_cost_of_living_covers_customer_cities(self):
        self.assertIn(CUSTOMER_PROFILE["prior_city"], COST_OF_LIVING)
        self.assertIn(CUSTOMER_PROFILE["current_city"], COST_OF_LIVING)

    def test_tax_reference_covers_customer_states(self):
        prior_state = CUSTOMER_PROFILE["prior_city"].split(",")[-1].strip()
        current_state = CUSTOMER_PROFILE["current_city"].split(",")[-1].strip()
        self.assertIn(prior_state, TAX_REFERENCE)
        self.assertIn(current_state, TAX_REFERENCE)

    def test_shopping_habits_derived_correctly(self):
        required_fields = {
            "avg_monthly_spend", "avg_transaction_amount", "total_transactions",
            "top_merchants", "online_share_percent", "in_store_share_percent",
        }
        self.assertTrue(required_fields.issubset(SHOPPING_HABITS.keys()))

        shopping_txns = [t for t in TRANSACTIONS if t["category"] == "shopping"]
        self.assertGreaterEqual(len(shopping_txns), 3, "Expected multiple shopping transactions")
        self.assertEqual(SHOPPING_HABITS["total_transactions"], len(shopping_txns))
        self.assertGreater(len(SHOPPING_HABITS["top_merchants"]), 0)


# ===========================================================================
class TestBankPolicies(unittest.TestCase):
    """Verify bank policies are complete and properly structured."""

    def test_all_policy_sections_exist(self):
        required_sections = [
            "account_policies", "credit_card_policies", "savings_and_goals",
            "loan_policies", "security_policies", "customer_support",
        ]
        for section in required_sections:
            self.assertIn(section, ATLAS_POLICIES)

    def test_overdraft_fee_is_specified(self):
        fee = ATLAS_POLICIES["account_policies"]["overdraft_protection"]["fee"]
        self.assertIn("$35", fee)

    def test_credit_card_apr_is_specified(self):
        apr_range = ATLAS_POLICIES["credit_card_policies"]["purchase_apr_range"]
        self.assertIsInstance(apr_range["min_apr"], (int, float))
        self.assertIsInstance(apr_range["max_apr"], (int, float))

    def test_savings_apy_is_specified(self):
        apy = ATLAS_POLICIES["savings_and_goals"]["high_yield_savings"]["apy"]
        self.assertTrue(apy)

    def test_student_loan_refi_requirements(self):
        refi = ATLAS_POLICIES["loan_policies"]["student_loan_refinancing"]
        self.assertIsInstance(refi["minimum_credit_score"], int)
        self.assertIn("10,000", refi["eligibility"])

    def test_support_hours_specified(self):
        hours = ATLAS_POLICIES["customer_support"]["in_app_chat"]["human_escalation_hours"]
        self.assertTrue(hours)

    def test_all_policy_values_are_nonempty(self):
        def check(value, path):
            if isinstance(value, dict):
                self.assertTrue(len(value) > 0, f"Empty dict at {path}")
                for key, val in value.items():
                    check(val, f"{path}.{key}")
            elif isinstance(value, list):
                self.assertTrue(len(value) > 0, f"Empty list at {path}")
                for i, item in enumerate(value):
                    check(item, f"{path}[{i}]")
            elif isinstance(value, str):
                self.assertTrue(value.strip(), f"Empty string at {path}")
            else:
                self.assertIsNotNone(value, f"None value at {path}")

        check(ATLAS_POLICIES, "ATLAS_POLICIES")


# ===========================================================================
class TestLifeEventTriggers(unittest.TestCase):
    """Verify the trigger system detects the planted signals correctly."""

    def setUp(self):
        self.scanner = LifeEventScanner(today=TODAY)

    def test_relocation_detected_high_confidence(self):
        result = self.scanner.detect_relocation(TRANSACTIONS, CUSTOMER_PROFILE)
        self.assertIsNotNone(result)
        self.assertEqual(result["confidence"], "high")
        self.assertTrue(len(result["evidence"]) > 0)

    def test_new_job_detected_high_confidence(self):
        result = self.scanner.detect_new_job(TRANSACTIONS, CUSTOMER_PROFILE)
        self.assertIsNotNone(result)
        self.assertEqual(result["confidence"], "high")
        current_employer = CUSTOMER_PROFILE["employment_history"][-1]["employer"]
        evidence_text = " ".join(t["description"] for t in result["evidence"])
        self.assertIn(current_employer.upper(), evidence_text.upper())

    def test_income_drop_not_falsely_triggered(self):
        result = self.scanner.detect_income_drop(TRANSACTIONS, CUSTOMER_PROFILE)
        self.assertTrue(result is None or result["confidence"] == "low")

    def test_subscription_creep_detection(self):
        sub_txns = [t for t in TRANSACTIONS if t["category"] == "subscription"]
        by_desc = {}
        for t in sub_txns:
            by_desc.setdefault(t["description"], []).append(t)
        latest_totals = sum(
            abs(sorted(txns, key=lambda t: t["date"])[-1]["amount"]) for txns in by_desc.values()
        )
        ratio = latest_totals / MONTHLY_SUMMARY["avg_monthly_income"]

        result = self.scanner.detect_subscription_creep(TRANSACTIONS, CUSTOMER_PROFILE, MONTHLY_SUMMARY)

        if ratio > 0.15:
            self.assertIsNotNone(result)
            self.assertEqual(result["confidence"], "high")
        else:
            self.assertTrue(result is None or result["confidence"] in ("medium", "low"))

    def test_low_confidence_events_filtered_by_scan_all(self):
        results = self.scanner.scan_all(
            TRANSACTIONS, CUSTOMER_PROFILE, FINANCIAL_PRODUCTS, MONTHLY_SUMMARY,
            NOTIFICATION_PREFERENCES, current_time=_daytime(),
        )
        for event in results:
            self.assertNotEqual(event["confidence"], "low")

    def test_scan_all_returns_high_before_medium(self):
        # Force a MEDIUM-confidence event (large upcoming payment) alongside the
        # baseline HIGH events, with a generous nudge limit so nothing gets
        # truncated before the ordering can be checked.
        products = copy.deepcopy(FINANCIAL_PRODUCTS)
        products["credit_card"]["payment_due_date"] = (TODAY + timedelta(days=3)).isoformat()
        products["checking"]["balance"] = (
            products["credit_card"]["minimum_payment"] + 100
        )
        prefs = dict(NOTIFICATION_PREFERENCES, max_nudges_per_week=10)

        scanner = LifeEventScanner(today=TODAY)
        results = scanner.scan_all(
            TRANSACTIONS, CUSTOMER_PROFILE, products, MONTHLY_SUMMARY, prefs,
            current_time=_daytime(),
        )
        confidences = [event["confidence"] for event in results]
        if "medium" in confidences:
            first_medium = confidences.index("medium")
            self.assertNotIn("high", confidences[first_medium:])

    def test_cooldown_suppresses_duplicate(self):
        scanner = LifeEventScanner(today=TODAY)
        first = scanner.scan_all(
            TRANSACTIONS, CUSTOMER_PROFILE, FINANCIAL_PRODUCTS, MONTHLY_SUMMARY,
            NOTIFICATION_PREFERENCES, current_time=_daytime(),
        )
        first_event_types = {event["event_type"] for event in first}
        self.assertTrue(len(first_event_types) > 0, "Expected at least one event on the first scan")

        second = scanner.scan_all(
            TRANSACTIONS, CUSTOMER_PROFILE, FINANCIAL_PRODUCTS, MONTHLY_SUMMARY,
            NOTIFICATION_PREFERENCES, current_time=_daytime(),
        )
        second_event_types = {event["event_type"] for event in second}
        self.assertTrue(first_event_types.isdisjoint(second_event_types))

    def test_nudge_limit_respected(self):
        products = copy.deepcopy(FINANCIAL_PRODUCTS)
        products["credit_card"]["payment_due_date"] = (TODAY + timedelta(days=3)).isoformat()
        products["checking"]["balance"] = products["credit_card"]["minimum_payment"] + 100
        prefs = dict(NOTIFICATION_PREFERENCES, max_nudges_per_week=1)

        scanner = LifeEventScanner(today=TODAY)
        results = scanner.scan_all(
            TRANSACTIONS, CUSTOMER_PROFILE, products, MONTHLY_SUMMARY, prefs,
            current_time=_daytime(),
        )
        self.assertLessEqual(len(results), 1)

    def test_each_trigger_returns_correct_schema(self):
        scanner = LifeEventScanner(today=TODAY)
        candidates = [
            scanner.detect_relocation(TRANSACTIONS, CUSTOMER_PROFILE),
            scanner.detect_new_job(TRANSACTIONS, CUSTOMER_PROFILE),
            scanner.detect_income_drop(TRANSACTIONS, CUSTOMER_PROFILE),
            scanner.detect_subscription_creep(TRANSACTIONS, CUSTOMER_PROFILE, MONTHLY_SUMMARY),
            scanner.detect_large_upcoming_payment(TRANSACTIONS, CUSTOMER_PROFILE, FINANCIAL_PRODUCTS),
            scanner.detect_travel(TRANSACTIONS, CUSTOMER_PROFILE),
        ]
        for result in candidates:
            if result is not None:
                self.assertEqual(set(result.keys()), REQUIRED_TRIGGER_SCHEMA_KEYS)

    def test_evidence_contains_real_transactions(self):
        scanner = LifeEventScanner(today=TODAY)
        candidates = [
            scanner.detect_relocation(TRANSACTIONS, CUSTOMER_PROFILE),
            scanner.detect_new_job(TRANSACTIONS, CUSTOMER_PROFILE),
        ]
        for result in candidates:
            if result is None:
                continue
            for txn in result["evidence"]:
                self.assertIn(txn, TRANSACTIONS)


def _daytime():
    from datetime import time
    return time(14, 0)


# ===========================================================================
class TestSystemPrompt(unittest.TestCase):
    """Verify the system prompt is complete and contains all required data."""

    @classmethod
    def setUpClass(cls):
        cls.prompt = build_system_prompt(
            CUSTOMER_PROFILE, FINANCIAL_PRODUCTS, CREDIT_PROFILE, FINANCIAL_GOALS,
            MONTHLY_SUMMARY, SHOPPING_HABITS, TRANSACTIONS, COST_OF_LIVING, TAX_REFERENCE,
            ATLAS_POLICIES,
        )

    def test_prompt_contains_bank_identity(self):
        self.assertIn("Atlas", self.prompt)
        self.assertIn("Atlas Assistant", self.prompt)

    def test_prompt_contains_customer_name(self):
        self.assertIn(CUSTOMER_PROFILE["name"], self.prompt)

    def test_prompt_contains_account_balances(self):
        formatted_balance = f"{FINANCIAL_PRODUCTS['checking']['balance']:,.2f}"
        self.assertIn(formatted_balance, self.prompt)

    def test_prompt_contains_credit_score(self):
        self.assertIn(str(CREDIT_PROFILE["score"]), self.prompt)

    def test_prompt_contains_grounding_rules(self):
        self.assertTrue(
            "provided below" in self.prompt or "CUSTOMER DATA" in self.prompt
        )

    def test_prompt_contains_unknown_info_example_phrasing(self):
        self.assertIn("don't have enough information", self.prompt.lower())
        self.assertIn("do not guess", self.prompt.lower())

    def test_prompt_contains_shopping_habits(self):
        self.assertIn("Shopping Habits", self.prompt)
        top_merchant_name = SHOPPING_HABITS["top_merchants"][0][0]
        self.assertIn(top_merchant_name, self.prompt)

    def test_prompt_contains_boundary_rules(self):
        self.assertIn("advisor", self.prompt.lower())
        self.assertIn("never", self.prompt.lower())

    def test_prompt_contains_privacy_rules(self):
        self.assertTrue(
            "account number" in self.prompt.lower() or "ssn" in self.prompt.lower()
        )

    def test_prompt_contains_bank_policies(self):
        found = sum(
            1 for value in ("$35", "4.15%", "25 days") if value in self.prompt
        )
        self.assertGreaterEqual(found, 3)

    def test_prompt_contains_ethical_guardrails(self):
        self.assertTrue(
            "distress" in self.prompt.lower() or "211.org" in self.prompt
        )

    def test_prompt_does_not_contain_raw_account_numbers(self):
        self.assertIsNone(re.search(r"\b\d{9,}\b", self.prompt))

    def test_prompt_does_not_contain_salary(self):
        # Salary is confidential and must never reach the model's context.
        self.assertNotIn("108,000", self.prompt)
        self.assertNotIn("108000", self.prompt)
        self.assertNotIn("salary", self.prompt.lower())

    def test_prompt_length_is_reasonable(self):
        self.assertTrue(3000 <= len(self.prompt) <= 20000, f"Prompt length was {len(self.prompt)}")


# ===========================================================================
class TestAppIntegration(unittest.TestCase):
    """Verify the app module's components wire together correctly without
    needing a real API key or a running Streamlit server."""

    def test_app_imports_without_error(self):
        import app  # noqa: F401 — import success is the assertion

    def test_system_prompt_builds_with_all_data(self):
        prompt = build_system_prompt(
            CUSTOMER_PROFILE, FINANCIAL_PRODUCTS, CREDIT_PROFILE, FINANCIAL_GOALS,
            MONTHLY_SUMMARY, SHOPPING_HABITS, TRANSACTIONS, COST_OF_LIVING, TAX_REFERENCE,
            ATLAS_POLICIES,
        )
        self.assertIsInstance(prompt, str)
        self.assertTrue(len(prompt) > 0)

    def test_life_event_scanner_runs_on_mock_data(self):
        scanner = LifeEventScanner(today=TODAY)
        results = scanner.scan_all(
            TRANSACTIONS, CUSTOMER_PROFILE, FINANCIAL_PRODUCTS, MONTHLY_SUMMARY,
            NOTIFICATION_PREFERENCES, current_time=_daytime(),
        )
        self.assertIsInstance(results, list)

    def test_triggered_events_produce_valid_nudge_context(self):
        scanner = LifeEventScanner(today=TODAY)
        results = scanner.scan_all(
            TRANSACTIONS, CUSTOMER_PROFILE, FINANCIAL_PRODUCTS, MONTHLY_SUMMARY,
            NOTIFICATION_PREFERENCES, current_time=_daytime(),
        )
        for event in results:
            self.assertIsInstance(event["suggested_context"], str)
            self.assertTrue(len(event["suggested_context"]) > 0)


# ===========================================================================
if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for test_class in (
        TestMockDataIntegrity,
        TestBankPolicies,
        TestLifeEventTriggers,
        TestSystemPrompt,
        TestAppIntegration,
    ):
        suite.addTests(loader.loadTestsFromTestCase(test_class))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 70)
    if result.wasSuccessful():
        print(f"PASS — {result.testsRun} tests passed, 0 failures, 0 errors")
        print("=" * 70)
        sys.exit(0)
    else:
        print(
            f"FAIL — {result.testsRun} tests run, "
            f"{len(result.failures)} failures, {len(result.errors)} errors"
        )
        print("=" * 70)
        sys.exit(1)
