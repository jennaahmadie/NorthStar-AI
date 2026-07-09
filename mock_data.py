"""
mock_data.py — Synthetic customer & reference data for the Atlas Bank
"Life Admin Assistant" demo.

This file represents what a real bank's core systems already know about a
customer: KYC profile, account balances, credit bureau data, and a rolling
transaction ledger. In production these would come from separate services
(identity, ledger, credit bureau feed) — here they're static Python objects
so the rest of the app can be built and demoed without real banking
infrastructure.

Design note: transaction dates are generated relative to today's date
(`TODAY`, computed at import time) rather than hardcoded, so the "life
event" signals planted in the last few weeks always look recent no matter
when this demo is actually run.
"""

from datetime import date, timedelta

TODAY = date.today()


def _d(days_ago: int) -> str:
    """Return an ISO date string `days_ago` days before today."""
    return (TODAY - timedelta(days=days_ago)).isoformat()


def _future(days_ahead: int) -> str:
    """Return an ISO date string `days_ahead` days after today."""
    return (TODAY + timedelta(days=days_ahead)).isoformat()


# ---------------------------------------------------------------------------
# CUSTOMER PROFILE
# ---------------------------------------------------------------------------

CUSTOMER_PROFILE = {
    "name": "Alex Rivera",
    "age": 24,
    "date_of_birth": "2002-03-15",
    "marital_status": "Single",
    "dependents": 0,
    "education": "B.S. Computer Science, UT Austin, 2024",
    "employment_history": [
        {
            "employer": "Crestline Software",
            "title": "Junior Software Developer",
            "city": "Austin, TX",
            "start_date": "2024-07-01",
            "end_date": _d(14),  # left ~2 weeks ago
        },
        {
            "employer": "Nimbus Analytics",
            "title": "Software Engineer",
            "city": "San Francisco, CA",
            "start_date": _d(8),  # started ~1 week ago
            "end_date": None,  # current job
        },
    ],
    "prior_city": "Austin, TX",
    "current_city": "San Francisco, CA",
    "phone": "(512) 555-0147",
    "email": "alex.rivera@email.com",
    "member_since": "2020-09-01",
}

CURRENT_EMPLOYER = CUSTOMER_PROFILE["employment_history"][-1]["employer"]
PRIOR_EMPLOYER = CUSTOMER_PROFILE["employment_history"][0]["employer"]


# ---------------------------------------------------------------------------
# FINANCIAL PRODUCTS (accounts held at Atlas Bank)
# ---------------------------------------------------------------------------

FINANCIAL_PRODUCTS = {
    "checking": {
        "account_number_masked": "****4821",
        "balance": 3120.44,
    },
    "savings": {
        "account_number_masked": "****9053",
        "balance": 0.00,
        "monthly_auto_transfer": 0,  # not set up yet
    },
    "credit_card": {
        "account_number_masked": "****7734",
        "credit_limit": 8000,
        "current_balance": 2340.00,
        "apr": 22.99,
        "minimum_payment": 47.00,
        "payment_due_date": _future(16),
        "rewards_type": "1.5% cashback",
    },
    "student_loans": {
        "servicer": "Great Lakes",
        "original_balance": 38000,
        "remaining_balance": 31200,
        "interest_rate": 5.5,
        "monthly_payment": 420,
        "expected_payoff_date": "2034-06",
    },
}


# ---------------------------------------------------------------------------
# CREDIT PROFILE
# ---------------------------------------------------------------------------

CREDIT_PROFILE = {
    "score": 691,
    "score_range": "Fair",
    "factors_helping": [
        "On-time payments (36 months)",
        "Low number of accounts",
    ],
    "factors_hurting": [
        "High credit utilization (29%)",
        "Short credit history",
        "No mortgage or installment loan mix",
    ],
}


# ---------------------------------------------------------------------------
# FINANCIAL GOALS (set during onboarding)
# ---------------------------------------------------------------------------

FINANCIAL_GOALS = [
    "Build an emergency fund (3 months expenses)",
    "Pay off credit card balance",
    "Start saving for an apartment deposit",
]


# ---------------------------------------------------------------------------
# NOTIFICATION PREFERENCES
# ---------------------------------------------------------------------------

NOTIFICATION_PREFERENCES = {
    "proactive_nudges": True,
    "max_nudges_per_week": 2,
    "preferred_channel": "in_app",
    "quiet_hours": "10pm-8am",
}


# ---------------------------------------------------------------------------
# TRANSACTIONS
#
# Stored as (days_ago, description, amount, category, merchant_type) tuples
# and expanded into full transaction dicts below. Negative amounts = money
# out, positive = money in. This mirrors how a ledger export would read.
#
# The most recent ~3 weeks intentionally contain the "life event" signals:
# a stopped rent payment, a moving company charge, a new-city security
# deposit, a switch to a new employer's payroll deposit, and new SF-area
# merchants appearing.
# ---------------------------------------------------------------------------

_RAW_TRANSACTIONS = [
    # --- Prior employer payroll (monthly, stops after the job change) ---
    (164, "CRESTLINE SOFTWARE PAYROLL DEP", 3260.00, "income", "employer_prior"),
    (134, "CRESTLINE SOFTWARE PAYROLL DEP", 3260.00, "income", "employer_prior"),
    (104, "CRESTLINE SOFTWARE PAYROLL DEP", 3298.50, "income", "employer_prior"),
    (74, "CRESTLINE SOFTWARE PAYROLL DEP", 3260.00, "income", "employer_prior"),
    (44, "CRESTLINE SOFTWARE PAYROLL DEP", 3260.00, "income", "employer_prior"),
    (14, "CRESTLINE SOFTWARE PAYROLL DEP", 3212.75, "income", "employer_prior"),

    # --- New employer payroll (life event signal: new job) ---
    (1, "NIMBUS ANALYTICS PAYROLL DEP", 6450.00, "income", "employer_current"),

    # --- Student loan payments (steady, unaffected by the job change) ---
    (159, "GREAT LAKES STUDENT LOAN PMT", -420.00, "loan_payment", "loan_servicer"),
    (129, "GREAT LAKES STUDENT LOAN PMT", -420.00, "loan_payment", "loan_servicer"),
    (99, "GREAT LAKES STUDENT LOAN PMT", -420.00, "loan_payment", "loan_servicer"),
    (69, "GREAT LAKES STUDENT LOAN PMT", -420.00, "loan_payment", "loan_servicer"),
    (39, "GREAT LAKES STUDENT LOAN PMT", -420.00, "loan_payment", "loan_servicer"),
    (9, "GREAT LAKES STUDENT LOAN PMT", -420.00, "loan_payment", "loan_servicer"),

    # --- Rent to prior (Austin) landlord — stops ~5 weeks ago ---
    (159, "AUSTIN OAKS APARTMENTS - RENT", -1400.00, "housing", "landlord"),
    (128, "AUSTIN OAKS APARTMENTS - RENT", -1400.00, "housing", "landlord"),
    (97, "AUSTIN OAKS APARTMENTS - RENT", -1400.00, "housing", "landlord"),
    (66, "AUSTIN OAKS APARTMENTS - RENT", -1400.00, "housing", "landlord"),
    (35, "AUSTIN OAKS APARTMENTS - RENT", -1400.00, "housing", "landlord"),

    # --- Subscriptions ---
    (153, "NETFLIX.COM", -15.49, "subscription", "streaming_service"),
    (123, "NETFLIX.COM", -15.49, "subscription", "streaming_service"),
    (93, "NETFLIX.COM", -15.49, "subscription", "streaming_service"),
    (63, "NETFLIX.COM", -15.49, "subscription", "streaming_service"),
    (33, "NETFLIX.COM", -15.49, "subscription", "streaming_service"),
    (3, "NETFLIX.COM", -15.49, "subscription", "streaming_service"),

    (157, "SPOTIFY USA", -11.99, "subscription", "streaming_service"),
    (127, "SPOTIFY USA", -11.99, "subscription", "streaming_service"),
    (97, "SPOTIFY USA", -11.99, "subscription", "streaming_service"),
    (67, "SPOTIFY USA", -11.99, "subscription", "streaming_service"),
    (37, "SPOTIFY USA", -11.99, "subscription", "streaming_service"),
    (7, "SPOTIFY USA", -11.99, "subscription", "streaming_service"),

    (155, "EQUINOX FITNESS CLUB", -189.00, "subscription", "fitness"),
    (125, "EQUINOX FITNESS CLUB", -189.00, "subscription", "fitness"),
    (95, "EQUINOX FITNESS CLUB", -189.00, "subscription", "fitness"),
    (65, "EQUINOX FITNESS CLUB", -189.00, "subscription", "fitness"),
    (35, "EQUINOX FITNESS CLUB", -189.00, "subscription", "fitness"),
    (5, "EQUINOX FITNESS CLUB", -189.00, "subscription", "fitness"),

    (162, "APPLE.COM/BILL - ICLOUD+", -2.99, "subscription", "cloud_storage"),
    (132, "APPLE.COM/BILL - ICLOUD+", -2.99, "subscription", "cloud_storage"),
    (102, "APPLE.COM/BILL - ICLOUD+", -2.99, "subscription", "cloud_storage"),
    (72, "APPLE.COM/BILL - ICLOUD+", -2.99, "subscription", "cloud_storage"),
    (42, "APPLE.COM/BILL - ICLOUD+", -2.99, "subscription", "cloud_storage"),
    (12, "APPLE.COM/BILL - ICLOUD+", -2.99, "subscription", "cloud_storage"),

    (115, "HELLOFRESH", -59.99, "subscription", "meal_kit"),
    (80, "HELLOFRESH", -59.99, "subscription", "meal_kit"),
    (45, "HELLOFRESH", -59.99, "subscription", "meal_kit"),
    (10, "HELLOFRESH", -59.99, "subscription", "meal_kit"),

    # --- Insurance & utilities ---
    (156, "GEICO AUTO INSURANCE", -95.00, "insurance", "insurance_provider"),
    (126, "GEICO AUTO INSURANCE", -95.00, "insurance", "insurance_provider"),
    (96, "GEICO AUTO INSURANCE", -95.00, "insurance", "insurance_provider"),
    (66, "GEICO AUTO INSURANCE", -95.00, "insurance", "insurance_provider"),
    (36, "GEICO AUTO INSURANCE", -95.00, "insurance", "insurance_provider"),
    (6, "GEICO AUTO INSURANCE", -95.00, "insurance", "insurance_provider"),

    (158, "VERIZON WIRELESS", -45.00, "utilities", "telecom"),
    (128, "VERIZON WIRELESS", -47.32, "utilities", "telecom"),
    (98, "VERIZON WIRELESS", -45.00, "utilities", "telecom"),
    (68, "VERIZON WIRELESS", -45.00, "utilities", "telecom"),
    (38, "VERIZON WIRELESS", -45.00, "utilities", "telecom"),
    (8, "VERIZON WIRELESS", -45.00, "utilities", "telecom"),

    # --- Credit card payments (sometimes minimum, sometimes more) ---
    (140, "ATLAS BANK CREDIT CARD PAYMENT", -200.00, "credit_card_payment", "bank_internal"),
    (110, "ATLAS BANK CREDIT CARD PAYMENT", -47.00, "credit_card_payment", "bank_internal"),
    (80, "ATLAS BANK CREDIT CARD PAYMENT", -120.00, "credit_card_payment", "bank_internal"),
    (50, "ATLAS BANK CREDIT CARD PAYMENT", -47.00, "credit_card_payment", "bank_internal"),
    (22, "ATLAS BANK CREDIT CARD PAYMENT", -75.00, "credit_card_payment", "bank_internal"),

    # --- Life event signals: relocation ---
    (20, "CROSS COUNTRY MOVERS", -2000.00, "moving", "moving_company"),
    (15, "BAY AREA PROPERTY MGMT - DEPOSIT", -2900.00, "housing", "property_management"),

    # --- New SF-area merchants appearing (relocation signal) ---
    (8, "WHOLE FOODS MARKET #4521 SF", -84.32, "groceries", "grocery_store"),
    (6, "BLUE BOTTLE COFFEE - SF", -6.75, "dining", "coffee_shop"),
    (5, "PHILZ COFFEE - SF", -5.50, "dining", "coffee_shop"),
    (4, "TARTINE BAKERY - SF", -18.40, "dining", "bakery"),
    (3, "LYFT *RIDE SF", -22.15, "rideshare", "rideshare_app"),
    (2, "WHOLE FOODS MARKET #4521 SF", -56.10, "groceries", "grocery_store"),
    (2, "SF MUNI - CLIPPER CARD", -25.00, "transportation", "transit"),
    (0, "BLUE BOTTLE COFFEE - SF", -7.25, "dining", "coffee_shop"),

    # --- Variable Austin-era spending (fills out realistic history) ---
    (25, "H-E-B GROCERY #234", -62.18, "groceries", "grocery_store"),
    (90, "H-E-B GROCERY #234", -58.20, "groceries", "grocery_store"),
    (40, "TRADER JOE'S AUSTIN", -45.60, "groceries", "grocery_store"),
    (28, "TORCHY'S TACOS", -14.75, "dining", "restaurant"),
    (100, "UCHI AUSTIN", -68.00, "dining", "restaurant"),
    (33, "UBER *TRIP", -18.40, "rideshare", "rideshare_app"),
    (60, "UBER *TRIP", -21.90, "rideshare", "rideshare_app"),

    # --- Shopping habits (mostly online, a mix of clothing/electronics/home) ---
    (45, "AMAZON.COM*MK4TP", -89.99, "shopping", "e_commerce"),
    (18, "AMAZON.COM*PN3KL", -124.50, "shopping", "e_commerce"),
    (105, "AMAZON.COM*7QWZR", -42.30, "shopping", "e_commerce"),
    (115, "ZARA USA", -78.50, "shopping", "retail"),
    (52, "TARGET T-1092", -67.20, "shopping", "retail"),
    (77, "BEST BUY #519", -215.99, "shopping", "electronics_store"),
    (135, "SEPHORA", -54.30, "shopping", "retail"),

    # --- One-off purchases ---
    (70, "TICKETMASTER - CONCERT", -145.00, "entertainment", "entertainment_venue"),
]

TRANSACTIONS = sorted(
    (
        {
            "date": _d(days_ago),
            "description": description,
            "amount": amount,
            "category": category,
            "merchant_type": merchant_type,
        }
        for days_ago, description, amount, category, merchant_type in _RAW_TRANSACTIONS
    ),
    key=lambda txn: txn["date"],
)


# ---------------------------------------------------------------------------
# MONTHLY SUMMARY
#
# Derived from the last 90 days of TRANSACTIONS, the same way a nightly
# aggregation job would compute a "trailing 3-month" feature set from the
# raw ledger. Kept as code (not hardcoded numbers) so it can never drift
# out of sync with the transactions above.
# ---------------------------------------------------------------------------

def _build_monthly_summary(transactions):
    cutoff = (TODAY - timedelta(days=90)).isoformat()
    recent = [t for t in transactions if t["date"] >= cutoff]

    total_income = sum(t["amount"] for t in recent if t["amount"] > 0)
    total_spending = sum(-t["amount"] for t in recent if t["amount"] < 0)

    avg_monthly_income = round(total_income / 3, 2)
    avg_monthly_spending = round(total_spending / 3, 2)
    avg_monthly_savings_rate = (
        round((avg_monthly_income - avg_monthly_spending) / avg_monthly_income * 100, 1)
        if avg_monthly_income
        else 0.0
    )

    def total_for(predicate):
        return round(sum(-t["amount"] for t in recent if predicate(t)) / 3, 2)

    top_spending_categories = sorted(
        [
            ("Rent", total_for(lambda t: t["merchant_type"] == "landlord")),
            ("Dining & Coffee", total_for(lambda t: t["category"] == "dining")),
            ("Rideshare", total_for(lambda t: t["category"] == "rideshare")),
            ("Groceries", total_for(lambda t: t["category"] == "groceries")),
            ("Subscriptions", total_for(lambda t: t["category"] == "subscription")),
            ("Student Loan", total_for(lambda t: t["category"] == "loan_payment")),
        ],
        key=lambda pair: pair[1],
        reverse=True,
    )

    return {
        "avg_monthly_income": avg_monthly_income,
        "avg_monthly_spending": avg_monthly_spending,
        "avg_monthly_savings_rate": avg_monthly_savings_rate,
        "top_spending_categories": top_spending_categories,
    }


MONTHLY_SUMMARY = _build_monthly_summary(TRANSACTIONS)


# ---------------------------------------------------------------------------
# SHOPPING HABITS
#
# Derived from every "shopping" category transaction in the ledger, the same
# way the monthly summary above is derived — not hardcoded, so it can never
# drift out of sync with TRANSACTIONS.
# ---------------------------------------------------------------------------

def _build_shopping_habits(transactions):
    shopping_txns = [t for t in transactions if t["category"] == "shopping"]
    if not shopping_txns:
        return {
            "avg_monthly_spend": 0,
            "avg_transaction_amount": 0,
            "total_transactions": 0,
            "top_merchants": [],
            "online_share_percent": 0,
            "in_store_share_percent": 0,
        }

    total_spent = sum(-t["amount"] for t in shopping_txns)
    count = len(shopping_txns)

    by_merchant = {}
    for t in shopping_txns:
        by_merchant[t["description"]] = by_merchant.get(t["description"], 0) - t["amount"]
    top_merchants = sorted(by_merchant.items(), key=lambda kv: kv[1], reverse=True)[:5]

    online_total = sum(-t["amount"] for t in shopping_txns if t["merchant_type"] == "e_commerce")
    online_share = round(online_total / total_spent * 100, 1) if total_spent else 0

    dates = sorted(date.fromisoformat(t["date"]) for t in shopping_txns)
    span_days = max((dates[-1] - dates[0]).days, 30)

    return {
        "avg_monthly_spend": round(total_spent / (span_days / 30), 2),
        "avg_transaction_amount": round(total_spent / count, 2),
        "total_transactions": count,
        "top_merchants": [(name, round(amount, 2)) for name, amount in top_merchants],
        "online_share_percent": online_share,
        "in_store_share_percent": round(100 - online_share, 1),
    }


SHOPPING_HABITS = _build_shopping_habits(TRANSACTIONS)


# ---------------------------------------------------------------------------
# COST OF LIVING REFERENCE (general benchmarks, not customer-specific)
# ---------------------------------------------------------------------------

COST_OF_LIVING = {
    "Austin, TX": {
        "median_1br_rent": 1450,
        "median_2br_rent": 1850,
        "avg_monthly_groceries": 380,
        "avg_monthly_transportation": 220,
        "recommended_rent_to_income_max": 0.30,
    },
    "San Francisco, CA": {
        "median_1br_rent": 2950,
        "median_2br_rent": 3900,
        "avg_monthly_groceries": 450,
        "avg_monthly_transportation": 180,
        "recommended_rent_to_income_max": 0.30,
    },
    "New York, NY": {
        "median_1br_rent": 3400,
        "median_2br_rent": 4300,
        "avg_monthly_groceries": 430,
        "avg_monthly_transportation": 132,
        "recommended_rent_to_income_max": 0.30,
    },
    "Chicago, IL": {
        "median_1br_rent": 1750,
        "median_2br_rent": 2300,
        "avg_monthly_groceries": 360,
        "avg_monthly_transportation": 105,
        "recommended_rent_to_income_max": 0.30,
    },
}


# ---------------------------------------------------------------------------
# TAX REFERENCE (general educational benchmarks, not personalized tax advice)
# ---------------------------------------------------------------------------

TAX_REFERENCE = {
    "TX": {
        "state_name": "Texas",
        "combined_effective_rate_by_income": {
            "$50,000": 0.16,
            "$100,000": 0.21,
            "$150,000": 0.25,
        },
        "notes": "Texas has no state income tax, so the combined rate here is federal only.",
    },
    "CA": {
        "state_name": "California",
        "combined_effective_rate_by_income": {
            "$50,000": 0.20,
            "$100,000": 0.27,
            "$150,000": 0.32,
        },
        "notes": "California has a progressive state income tax with rates up to 13.3% at the highest bracket.",
    },
    "NY": {
        "state_name": "New York",
        "combined_effective_rate_by_income": {
            "$50,000": 0.19,
            "$100,000": 0.26,
            "$150,000": 0.31,
        },
        "notes": "New York has a progressive state income tax, and NYC residents pay an additional city income tax.",
    },
    "IL": {
        "state_name": "Illinois",
        "combined_effective_rate_by_income": {
            "$50,000": 0.19,
            "$100,000": 0.24,
            "$150,000": 0.28,
        },
        "notes": "Illinois has a flat state income tax rate of 4.95%.",
    },
}
