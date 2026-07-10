"""
app.py — Streamlit chatbot UI for Atlas Assistant.

Meant to be embedded as a chat widget inside Atlas Bank's web/mobile
platform. All page-drawing logic lives inside main(), which only runs
when this file is launched via `streamlit run app.py` — so `import app`
(as the test suite does) is safe and side-effect-free.
"""

import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from groq import Groq

# Loads GROQ_API_KEY from a local .env file if one exists (see .env.example).
# No-op in deployments that set the key another way (env var, st.secrets).
load_dotenv()

from bank_policies import ATLAS_POLICIES
from life_event_triggers import LifeEventScanner
from mock_data import (
    CREDIT_PROFILE,
    CUSTOMER_PROFILE,
    FINANCIAL_GOALS,
    FINANCIAL_PRODUCTS,
    MONTHLY_SUMMARY,
    NOTIFICATION_PREFERENCES,
    SHOPPING_HABITS,
    TRANSACTIONS,
    COST_OF_LIVING,
    TAX_REFERENCE,
)
from system_prompt import build_system_prompt

MODEL_NAME = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = build_system_prompt(
    CUSTOMER_PROFILE,
    FINANCIAL_PRODUCTS,
    CREDIT_PROFILE,
    FINANCIAL_GOALS,
    MONTHLY_SUMMARY,
    SHOPPING_HABITS,
    TRANSACTIONS,
    COST_OF_LIVING,
    TAX_REFERENCE,
    ATLAS_POLICIES,
)

def escape_currency_for_markdown(text):
    """Streamlit's markdown renderer (used by st.markdown and st.info alike)
    treats a matched pair of '$' as LaTeX math delimiters, which silently
    swallows spaces/newlines between two dollar amounts in the same message
    (e.g. "$3,120.44 ... $2,340.00" renders as one glued-together
    expression). Escape every '$' so currency always shows as a literal
    dollar sign instead of triggering math mode.
    """
    return text.replace("$", "\\$")


DISCLAIMER = (
    "Atlas Assistant provides general financial guidance, not personalized financial "
    "advice. For investment, tax, or complex financial decisions, please consult a "
    "licensed advisor."
)


def get_api_key():
    """Look up the Groq API key from whichever source the current
    environment uses, so rotating the key never requires a code change:

    - Local dev: a .env file (loaded above) or an exported env var.
    - Streamlit Community Cloud: the app's Settings -> Secrets manager,
      read via st.secrets.
    - Other hosts (Docker, Render, Railway, etc.): a plain env var set in
      the platform's dashboard/config.

    Never hardcode a key in source — that's the one thing that *would*
    require a code change (and a commit) every time it rotates.
    """
    try:
        if "GROQ_API_KEY" in st.secrets:
            return st.secrets["GROQ_API_KEY"]
    except Exception:
        pass  # no secrets.toml configured in this environment — fall through
    return os.environ.get("GROQ_API_KEY")


def get_groq_client():
    """Build a Groq client from the currently configured API key."""
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Set it in a .env file, as an environment "
            "variable, or in Streamlit's Secrets manager — see README.md."
        )
    return Groq(api_key=api_key)


def generate_chat_response(conversation_history, system_prompt):
    """Send the full conversation (with the system prompt prepended) to Groq
    and return the assistant's reply text."""
    client = get_groq_client()
    messages = [{"role": "system", "content": system_prompt}] + conversation_history
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        max_tokens=800,
    )
    return response.choices[0].message.content


def generate_nudge_message(event, system_prompt):
    """Turn a rule-based trigger's `suggested_context` into a short,
    customer-facing proactive notification via a separate, constrained
    LLM call. The LLM only phrases the message — it never decides whether
    or when to notify the customer; that decision already happened in
    LifeEventScanner.
    """
    client = get_groq_client()
    instruction = (
        "Generate ONE proactive notification for the customer based on the detected "
        "context below. Follow the PROACTIVE NUDGE RULES in your instructions exactly: "
        "1-2 sentences maximum, frame it as an observation and offer (never a command), "
        "and do not mention detection logic or that a 'system' flagged anything.\n\n"
        f"Detected context: {event['suggested_context']}"
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": instruction},
    ]
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        max_tokens=150,
    )
    return response.choices[0].message.content


def render_sidebar():
    with st.sidebar:
        st.markdown("## Atlas Bank")
        st.caption("Life Admin Assistant")
        st.divider()

        st.markdown(f"**{CUSTOMER_PROFILE['name']}**")
        st.caption(f"Member since {CUSTOMER_PROFILE['member_since']}")
        st.caption(f"Currently in {CUSTOMER_PROFILE['current_city']}")

        st.divider()
        st.markdown("### Accounts")
        st.metric("Checking", f"${FINANCIAL_PRODUCTS['checking']['balance']:,.2f}")
        st.metric("Savings", f"${FINANCIAL_PRODUCTS['savings']['balance']:,.2f}")
        st.metric(
            "Credit Card Balance",
            f"${FINANCIAL_PRODUCTS['credit_card']['current_balance']:,.2f}",
        )
        st.metric(
            "Credit Score",
            f"{CREDIT_PROFILE['score']} ({CREDIT_PROFILE['score_range']})",
        )

        st.divider()
        st.markdown("### Your Goals")
        for goal in FINANCIAL_GOALS:
            st.markdown(f"- {goal}")

        st.divider()
        with st.expander("Recent Transactions"):
            recent = sorted(TRANSACTIONS, key=lambda t: t["date"], reverse=True)[:20]
            st.dataframe(pd.DataFrame(recent), hide_index=True, use_container_width=True)


def render_proactive_notifications():
    if "nudges_generated" not in st.session_state:
        st.session_state.nudges_generated = True
        st.session_state.proactive_messages = []

        scanner = LifeEventScanner()
        events = scanner.scan_all(
            TRANSACTIONS,
            CUSTOMER_PROFILE,
            financial_products=FINANCIAL_PRODUCTS,
            monthly_summary=MONTHLY_SUMMARY,
            notification_preferences=NOTIFICATION_PREFERENCES,
        )

        if get_api_key():
            for event in events:
                try:
                    message = generate_nudge_message(event, SYSTEM_PROMPT)
                except Exception as exc:
                    message = None
                    st.session_state.setdefault("nudge_errors", []).append(str(exc))
                if message:
                    st.session_state.proactive_messages.append(message)

    for message in st.session_state.get("proactive_messages", []):
        st.info(escape_currency_for_markdown(message))


def render_chat():
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(escape_currency_for_markdown(msg["content"]))

    user_input = st.chat_input("Ask about your accounts, a life event, or an Atlas policy...")
    if not user_input:
        return

    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(escape_currency_for_markdown(user_input))

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                reply = generate_chat_response(st.session_state.messages, SYSTEM_PROMPT)
            except RuntimeError:
                reply = (
                    "Atlas Assistant isn't fully configured yet — the GROQ_API_KEY "
                    "environment variable is missing. See README.md for setup steps."
                )
            except Exception as exc:
                reply = f"Something went wrong reaching Atlas Assistant: {exc}"
        st.markdown(escape_currency_for_markdown(reply))

    st.session_state.messages.append({"role": "assistant", "content": reply})


def main():
    st.set_page_config(page_title="Atlas Bank — Life Admin Assistant", layout="wide")

    render_sidebar()

    st.title("Atlas Bank — Life Admin Assistant")

    if not get_api_key():
        st.warning(
            "GROQ_API_KEY is not set, so chat responses are disabled. See README.md "
            "for how to get a free key from console.groq.com."
        )

    render_proactive_notifications()
    st.divider()
    render_chat()
    st.divider()
    st.caption(DISCLAIMER)


if __name__ == "__main__":
    main()
