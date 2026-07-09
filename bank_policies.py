"""
bank_policies.py — Atlas Bank's product and policy reference data.

This is the single source of truth the chatbot is allowed to quote from
when answering questions about fees, rates, and account features. The
system prompt embeds this dict verbatim so the model never has to guess
or fall back on generic banking knowledge.
"""

ATLAS_POLICIES = {
    "account_policies": {
        "overdraft_protection": {
            "description": (
                "If a purchase would overdraw your checking account, we can "
                "cover it up to a daily limit instead of declining the "
                "transaction. Coverage is opt-in and off by default."
            ),
            "fee": "$35 per overdraft item",
            "opt_in_method": "Toggle 'Overdraft Coverage' in the app under Account Settings",
            "daily_coverage_limit": "$500",
        },
        "minimum_balance": {
            "checking_minimum": "$0",
            "savings_minimum": "$100",
            "savings_fee_if_below_minimum": "$5 monthly fee",
        },
        "direct_deposit_bonus": {
            "amount": "$200",
            "requirement": "Set up direct deposit within 60 days of account opening",
        },
        "atm_fees": {
            "atlas_atms": "Free",
            "non_atlas_atms": "$2.50 per withdrawal",
            "premium_account_reimbursement": "Up to $10/month reimbursed on Premium accounts",
        },
        "wire_transfer_fees": {
            "domestic": "$25",
            "international": "$45",
        },
    },
    "credit_card_policies": {
        "late_payment_fee": {
            "first_occurrence": "$29",
            "subsequent_occurrences": "$39",
        },
        "grace_period": "25 days from statement close",
        "purchase_apr_range": {
            "min_apr": 18.99,
            "max_apr": 27.99,
            "description": "Variable APR assigned within this range based on creditworthiness",
        },
        "balance_transfer": {
            "fee": "3% of transferred amount",
            "intro_apr": "0% for 12 months on transfers made in the first 60 days",
        },
        "cash_advance": {
            "fee": "5% of advance amount",
            "grace_period": "None — interest accrues immediately",
            "apr": "24.99%",
        },
        "credit_limit_increase": {
            "eligibility": "6 months of on-time payments",
            "credit_check": "No hard pull for existing customers",
        },
        "rewards": {
            "base_rate": "1.5% cashback on all purchases",
            "dining_rate": "3% cashback on dining",
            "redemption_options": ["Statement credit", "Deposit to checking or savings"],
        },
    },
    "savings_and_goals": {
        "high_yield_savings": {
            "apy": "4.15%",
            "minimum_balance": "None",
            "max_transfers": "No limit on transfers out",
        },
        "goal_based_savings_buckets": {
            "description": (
                "Named sub-accounts (e.g. 'Emergency Fund', 'Apartment "
                "Deposit') with a target amount and target date, tracked "
                "separately from your main savings balance."
            ),
        },
        "auto_transfer_rules": {
            "description": "Recurring transfers from checking to savings on a schedule you set",
            "minimum_per_transfer": "$10",
        },
        "round_up_savings": {
            "description": (
                "Rounds every debit card purchase up to the nearest dollar "
                "and sweeps the difference into savings."
            ),
        },
    },
    "loan_policies": {
        "personal_loan": {
            "apr_range": "7.99%–15.99%, based on credit profile",
            "amount_range": "$2,000–$35,000",
            "term_range": "2–5 years",
        },
        "student_loan_refinancing": {
            "eligibility": "Balances over $10,000",
            "apr_starting_at": "4.99%",
            "minimum_credit_score": 680,
        },
        "mortgage_prequalification": {
            "description": "Available directly in the app",
            "credit_check": "No hard pull",
            "time_to_complete": "About 5 minutes",
        },
    },
    "security_policies": {
        "two_factor_authentication": "Required for all account changes",
        "fraud_alerts": (
            "Real-time notifications for transactions over $500 or in new locations"
        ),
        "card_lock": "Instant card freeze/unfreeze available in the app",
        "dispute_process": {
            "filing_window": "60 days from the transaction date",
            "provisional_credit": "Issued within 10 business days",
        },
    },
    "customer_support": {
        "in_app_chat": {
            "ai_assistant": "24/7 (this chatbot)",
            "human_escalation_hours": "8am–10pm ET",
        },
        "phone": {
            "number": "1-800-ATLAS",
            "hours": "8am–10pm ET",
        },
        "branch_appointments": "Bookable through the app",
        "financial_advisor_consultations": {
            "free_session": "30 minutes, for customers with $10,000+ in deposits",
            "standard_fee": "$50 for customers below that threshold",
        },
    },
}
