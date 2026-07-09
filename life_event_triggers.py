"""
life_event_triggers.py — Deterministic life event detection.

Architectural rule this file exists to enforce: DETECTION is always
rule-based. Every trigger below is a plain function of the transaction
ledger and profile data — no LLM call, no model judgment, nothing
probabilistic. The LLM is only ever invoked *after* a rule fires here, to
turn a structured `suggested_context` into a customer-facing sentence.
The model never decides on its own whose account to look at or when to
reach out — that decision is fully auditable Python.

Each detect_* method returns either:
    {"event_type": str, "confidence": "high"|"medium"|"low",
     "evidence": [transaction, ...], "suggested_context": str}
or None if the pattern isn't present.
"""

import re
from datetime import date, datetime, time, timedelta

# Common city abbreviations used in merchant descriptions, so a plain
# substring/word match can recognize "new city" merchant activity.
_CITY_ABBREVIATIONS = {
    "San Francisco": "SF",
    "New York": "NYC",
    "Austin": "ATX",
    "Chicago": "CHI",
}


def _city_tokens(city_state):
    """'San Francisco, CA' -> ['SAN FRANCISCO', 'SF']"""
    city = city_state.split(",")[0].strip()
    tokens = [city.upper()]
    if city in _CITY_ABBREVIATIONS:
        tokens.append(_CITY_ABBREVIATIONS[city])
    return tokens


def _mentions_city(description, city_state):
    desc_upper = description.upper()
    return any(
        re.search(r"\b" + re.escape(token) + r"\b", desc_upper)
        for token in _city_tokens(city_state)
    )


class LifeEventScanner:
    """Scans a customer's transaction history for rule-based life event patterns."""

    COOLDOWN_DAYS = 7
    RENT_STOPPED_THRESHOLD_DAYS = 28
    NEW_EMPLOYER_MIN_GAP_DAYS = 7

    def __init__(self, today=None):
        self.today = today or date.today()

        # In-memory cooldown/rate-limit state for this demo session only.
        # In production this would live in a database (e.g. a
        # `nudge_history` table keyed by customer_id + event_type) so it
        # persists across requests and app restarts.
        self._cooldowns = {}  # event_type -> date last triggered
        self._nudge_log = []  # list of dates a nudge was actually sent

    # ------------------------------------------------------------------
    # Detection rules
    # ------------------------------------------------------------------

    def detect_relocation(self, transactions, customer_profile):
        current_city = customer_profile.get("current_city")
        home_city = customer_profile.get("prior_city")

        moving_txns = [t for t in transactions if t["category"] == "moving"]
        deposit_txns = [
            t for t in transactions
            if t["category"] == "housing" and t["merchant_type"] == "property_management"
        ]
        new_city_txns = [
            t for t in transactions
            if current_city
            and _mentions_city(t["description"], current_city)
            and not (home_city and _mentions_city(t["description"], home_city))
        ]
        rent_txns = sorted(
            [t for t in transactions if t["merchant_type"] == "landlord"],
            key=lambda t: t["date"],
        )

        rent_stopped = False
        if rent_txns:
            last_rent_date = date.fromisoformat(rent_txns[-1]["date"])
            rent_stopped = (self.today - last_rent_date).days > self.RENT_STOPPED_THRESHOLD_DAYS

        has_moving = bool(moving_txns)
        has_deposit = bool(deposit_txns)
        has_new_city = bool(new_city_txns)

        if has_moving and (has_deposit or has_new_city) and rent_stopped:
            confidence = "high"
        elif has_moving or (has_deposit and rent_stopped):
            confidence = "medium"
        elif has_new_city:
            confidence = "low"
        else:
            return None

        signals = []
        if has_moving:
            signals.append("a moving company charge")
        if has_deposit:
            signals.append("a new security deposit")
        if has_new_city:
            signals.append(f"new merchants in {current_city}")
        if rent_stopped:
            signals.append("rent payments to the prior landlord stopping")

        evidence = moving_txns + deposit_txns + new_city_txns[:3]
        if rent_txns:
            evidence.append(rent_txns[-1])

        return {
            "event_type": "relocation",
            "confidence": confidence,
            "evidence": evidence,
            "suggested_context": (
                f"Signals suggest the customer may have relocated from {home_city} "
                f"to {current_city}: " + ", ".join(signals) + "."
            ),
        }

    def detect_new_job(self, transactions, customer_profile):
        income_txns = sorted(
            [t for t in transactions if t["category"] == "income"],
            key=lambda t: t["date"],
        )
        if not income_txns:
            return None

        by_desc = {}
        for t in income_txns:
            by_desc.setdefault(t["description"], []).append(t)

        newest_desc = income_txns[-1]["description"]
        newest_group = by_desc[newest_desc]
        other_descs = [d for d in by_desc if d != newest_desc]

        if other_descs:
            # A different payroll source exists in history -> possible employer switch.
            prior_desc = max(other_descs, key=lambda d: len(by_desc[d]))
            prior_group = sorted(by_desc[prior_desc], key=lambda t: t["date"])
            prior_last_date = date.fromisoformat(prior_group[-1]["date"])
            days_since_prior = (self.today - prior_last_date).days

            if len(newest_group) <= 2:
                evidence = newest_group + prior_group[-1:]
                if days_since_prior >= self.NEW_EMPLOYER_MIN_GAP_DAYS:
                    return {
                        "event_type": "new_job",
                        "confidence": "high",
                        "evidence": evidence,
                        "suggested_context": (
                            f"Payroll deposits appear to have switched from "
                            f"'{prior_desc}' to a new source, '{newest_desc}'. The "
                            f"prior employer's deposits stopped {days_since_prior} "
                            f"days ago."
                        ),
                    }
                return {
                    "event_type": "new_job",
                    "confidence": "low",
                    "evidence": evidence,
                    "suggested_context": (
                        f"A deposit from an unfamiliar source, '{newest_desc}', "
                        f"appeared recently, but it's too soon to tell if it "
                        f"replaces the customer's usual income."
                    ),
                }
            # Established second income stream — not treated as a job switch here.
            return None

        # Only one payroll source in history: check for a raise/promotion.
        sorted_group = sorted(newest_group, key=lambda t: t["date"])
        if len(sorted_group) < 2:
            return None
        latest_amount = sorted_group[-1]["amount"]
        prior_amounts = [t["amount"] for t in sorted_group[:-1]]
        avg_prior = sum(prior_amounts) / len(prior_amounts)
        if avg_prior <= 0:
            return None
        pct_change = (latest_amount - avg_prior) / avg_prior
        if pct_change > 0.20:
            return {
                "event_type": "new_job",
                "confidence": "medium",
                "evidence": sorted_group[-2:],
                "suggested_context": (
                    f"The customer's payroll deposit from '{newest_desc}' increased "
                    f"about {pct_change:.0%} versus their recent average, which may "
                    f"indicate a raise or promotion."
                ),
            }
        return None

    def detect_income_drop(self, transactions, customer_profile):
        income_txns = sorted(
            [t for t in transactions if t["category"] == "income"],
            key=lambda t: t["date"],
        )
        if len(income_txns) < 2:
            return None

        dates = [date.fromisoformat(t["date"]) for t in income_txns]
        gaps = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
        expected_interval = sorted(gaps)[len(gaps) // 2]  # median gap between deposits

        last_income_date = dates[-1]
        days_since_last_income = (self.today - last_income_date).days
        missed_periods = days_since_last_income // expected_interval if expected_interval > 0 else 0

        last_amount = income_txns[-1]["amount"]
        prev_amount = income_txns[-2]["amount"]
        pct_change = (last_amount - prev_amount) / prev_amount if prev_amount else 0

        if missed_periods >= 2 or pct_change <= -0.30:
            confidence = "high"
        elif missed_periods == 1:
            confidence = "medium"
        else:
            return None

        return {
            "event_type": "income_drop",
            "confidence": confidence,
            "evidence": income_txns[-2:],
            "suggested_context": (
                f"It has been {days_since_last_income} days since the customer's "
                f"last income deposit, versus a typical interval of about "
                f"{expected_interval} days. Handle this with extra care — frame "
                f"around support, not judgment."
            ),
        }

    def detect_subscription_creep(self, transactions, customer_profile, monthly_summary=None):
        sub_txns = [t for t in transactions if t["category"] == "subscription"]
        if not sub_txns:
            return None

        by_desc = {}
        for t in sub_txns:
            by_desc.setdefault(t["description"], []).append(t)

        latest_per_sub = {
            desc: sorted(txns, key=lambda t: t["date"])[-1] for desc, txns in by_desc.items()
        }
        current_monthly_total = sum(abs(t["amount"]) for t in latest_per_sub.values())
        evidence = list(latest_per_sub.values())

        if monthly_summary and monthly_summary.get("avg_monthly_income"):
            monthly_income = monthly_summary["avg_monthly_income"]
        else:
            cutoff = (self.today - timedelta(days=90)).isoformat()
            income_total = sum(
                t["amount"] for t in transactions
                if t["category"] == "income" and t["date"] >= cutoff
            )
            monthly_income = income_total / 3 if income_total else None

        if monthly_income:
            ratio = current_monthly_total / monthly_income
            if ratio > 0.15:
                return {
                    "event_type": "subscription_creep",
                    "confidence": "high",
                    "evidence": evidence,
                    "suggested_context": (
                        f"Subscriptions total about ${current_monthly_total:.2f}/month, "
                        f"roughly {ratio:.0%} of average monthly income."
                    ),
                }

        cutoff_60 = (self.today - timedelta(days=60)).isoformat()
        first_seen = {desc: min(t["date"] for t in txns) for desc, txns in by_desc.items()}
        new_subs = [desc for desc, first in first_seen.items() if first >= cutoff_60]
        if len(new_subs) >= 3:
            return {
                "event_type": "subscription_creep",
                "confidence": "medium",
                "evidence": [latest_per_sub[d] for d in new_subs],
                "suggested_context": (
                    f"{len(new_subs)} new subscriptions were added in the last 60 days."
                ),
            }

        cutoff_30 = (self.today - timedelta(days=30)).isoformat()
        last_30_total = sum(abs(t["amount"]) for t in sub_txns if t["date"] >= cutoff_30)
        prior_30_total = sum(
            abs(t["amount"]) for t in sub_txns if cutoff_60 <= t["date"] < cutoff_30
        )
        if prior_30_total > 0:
            mom_change = (last_30_total - prior_30_total) / prior_30_total
            if mom_change > 0.20:
                return {
                    "event_type": "subscription_creep",
                    "confidence": "low",
                    "evidence": evidence,
                    "suggested_context": (
                        f"Subscription spending increased about {mom_change:.0%} "
                        f"month-over-month."
                    ),
                }

        return None

    def detect_large_upcoming_payment(self, transactions, customer_profile, financial_products):
        cc = financial_products.get("credit_card", {})
        checking = financial_products.get("checking", {})
        due_date_str = cc.get("payment_due_date")
        if not due_date_str:
            return None

        due_date = date.fromisoformat(due_date_str)
        days_until_due = (due_date - self.today).days
        if not (0 <= days_until_due <= 7):
            return None

        checking_balance = checking.get("balance", 0)
        minimum_payment = cc.get("minimum_payment", 0)
        statement_balance = cc.get("current_balance", 0)

        if checking_balance < minimum_payment:
            confidence = "high"
        elif checking_balance < statement_balance:
            confidence = "medium"
        else:
            return None

        evidence = sorted(
            [t for t in transactions if t["category"] == "credit_card_payment"],
            key=lambda t: t["date"],
        )[-1:]

        return {
            "event_type": "large_upcoming_payment",
            "confidence": confidence,
            "evidence": evidence,
            "suggested_context": (
                f"A credit card payment of ${statement_balance:.2f} is due in "
                f"{days_until_due} day(s), and the checking balance may not fully "
                f"cover it."
            ),
        }

    def detect_travel(self, transactions, customer_profile):
        airline_txns = sorted(
            [t for t in transactions if t.get("merchant_type") == "airline"],
            key=lambda t: t["date"],
        )
        if not airline_txns:
            return None

        hotel_txns = sorted(
            [t for t in transactions if t.get("merchant_type") == "hotel"],
            key=lambda t: t["date"],
        )
        for airline_txn in airline_txns:
            a_date = date.fromisoformat(airline_txn["date"])
            for hotel_txn in hotel_txns:
                h_date = date.fromisoformat(hotel_txn["date"])
                if abs((h_date - a_date).days) <= 7:
                    return {
                        "event_type": "travel",
                        "confidence": "high",
                        "evidence": [airline_txn, hotel_txn],
                        "suggested_context": (
                            "Airline and hotel charges within the same week suggest "
                            "the customer is traveling. Consider mentioning foreign "
                            "transaction fees and travel notifications for their card."
                        ),
                    }

        return {
            "event_type": "travel",
            "confidence": "medium",
            "evidence": airline_txns[-1:],
            "suggested_context": (
                "An airline charge suggests upcoming travel. Consider mentioning "
                "foreign transaction fees and travel notifications for their card."
            ),
        }

    # ------------------------------------------------------------------
    # Orchestration
    # ------------------------------------------------------------------

    def scan_all(
        self,
        transactions,
        customer_profile,
        financial_products=None,
        monthly_summary=None,
        notification_preferences=None,
        current_time=None,
    ):
        """Run every detector, apply filtering/cooldown/rate-limit rules,
        and return triggered events sorted HIGH-confidence first."""

        notification_preferences = notification_preferences or {}
        if not notification_preferences.get("proactive_nudges", True):
            return []

        current_time = current_time if current_time is not None else datetime.now().time()
        if self._in_quiet_hours(current_time, notification_preferences.get("quiet_hours")):
            return []

        candidates = [
            self.detect_relocation(transactions, customer_profile),
            self.detect_new_job(transactions, customer_profile),
            self.detect_income_drop(transactions, customer_profile),
            self.detect_subscription_creep(transactions, customer_profile, monthly_summary),
            self.detect_travel(transactions, customer_profile),
        ]
        if financial_products:
            candidates.append(
                self.detect_large_upcoming_payment(transactions, customer_profile, financial_products)
            )

        # Only HIGH/MEDIUM confidence events are ever surfaced to a customer.
        filtered = [c for c in candidates if c and c["confidence"] in ("high", "medium")]

        # Skip event types that already fired within the cooldown window.
        filtered = [c for c in filtered if not self._in_cooldown(c["event_type"])]

        order = {"high": 0, "medium": 1}
        filtered.sort(key=lambda c: order[c["confidence"]])

        max_nudges = notification_preferences.get("max_nudges_per_week", 2)
        remaining_slots = max(0, max_nudges - self._nudges_sent_in_last_7_days())
        selected = filtered[:remaining_slots]

        for event in selected:
            self._record_trigger(event["event_type"])

        return selected

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _in_cooldown(self, event_type):
        last_triggered = self._cooldowns.get(event_type)
        if not last_triggered:
            return False
        return (self.today - last_triggered).days < self.COOLDOWN_DAYS

    def _record_trigger(self, event_type):
        self._cooldowns[event_type] = self.today
        self._nudge_log.append(self.today)

    def _nudges_sent_in_last_7_days(self):
        return sum(1 for d in self._nudge_log if (self.today - d).days < 7)

    @staticmethod
    def _parse_clock_hour(token):
        token = token.strip().lower()
        is_pm = "pm" in token
        num = int(token.replace("am", "").replace("pm", "").strip())
        hour = num % 12
        if is_pm:
            hour += 12
        return time(hour, 0)

    def _in_quiet_hours(self, current_time, quiet_hours_str):
        if not quiet_hours_str or "-" not in quiet_hours_str:
            return False
        try:
            start_str, end_str = quiet_hours_str.split("-")
            start = self._parse_clock_hour(start_str)
            end = self._parse_clock_hour(end_str)
        except ValueError:
            return False

        if start <= end:
            return start <= current_time <= end
        return current_time >= start or current_time <= end
