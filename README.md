# Atlas Bank — Life Admin Assistant (NorthStar AI)

A chatbot MVP for **Atlas Bank**, a fictional digital-first bank for young
professionals (22–35). The assistant is embedded in Atlas's platform and
helps customers navigate major life moments — starting a job, moving,
graduating, having a child — using their own account data, and proactively
reaches out when it detects a life change from their transaction patterns.

Built with [Streamlit](https://streamlit.io) for the UI and the
[Groq Cloud API](https://console.groq.com) running Llama 3.3 70B for the
chat model.

## Architecture at a glance

| File | Responsibility |
|---|---|
| `mock_data.py` | Synthetic customer profile, accounts, credit data, and a 4–6 month transaction ledger with "life event" signals planted in the last few weeks |
| `bank_policies.py` | Atlas Bank's actual product policies (fees, rates, terms) — the only source the bot is allowed to quote from |
| `life_event_triggers.py` | Deterministic, rule-based detection of life events from transaction patterns (relocation, new job, income drop, subscription creep, large upcoming payment, travel) |
| `system_prompt.py` | Builds the single system prompt: identity, grounding rules, boundaries, tone, and all embedded customer/policy data |
| `app.py` | Streamlit UI — sidebar account overview, proactive notifications, and the chat interface |
| `test_strict.py` | Full test suite covering data integrity, policies, triggers, the prompt, and app wiring |

**Key design decision:** life event *detection* is 100% rule-based Python
(`life_event_triggers.py`). The LLM is only ever called *after* a rule
fires, to phrase a short customer-facing message from a structured
`suggested_context`. The model never decides on its own when to contact a
customer.

## Setup

### 1. Get a free Groq API key

1. Go to [console.groq.com](https://console.groq.com) and sign up (free).
2. Create an API key from the dashboard.

### 2. Install dependencies

```bash
python3 -m venv venv
source venv/bin/activate   # on Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Set your API key

```bash
export GROQ_API_KEY="your-key-here"
```

(On Windows PowerShell: `$env:GROQ_API_KEY="your-key-here"`)

### 4. Run the app

```bash
streamlit run app.py
```

This opens the app in your browser, usually at `http://localhost:8501`.

## Running the tests

```bash
python3 test_strict.py
```

All tests should pass with 0 failures before presenting the demo.

## What to test in the live demo

1. **Proactive detection on load** — the app should surface two proactive
   notifications automatically: one about the recent move (Austin → San
   Francisco) and one about the new job at Nimbus Analytics. These are
   generated from rule-based triggers, not the model guessing.
2. **Grounded Q&A** — ask "What's my checking balance?" or "What's my
   credit score?" and confirm the answer matches the exact figures in
   `mock_data.py`, not an approximation.
3. **Boundary enforcement** — ask "Should I invest my savings in Bitcoin?"
   and confirm the assistant declines and redirects to a licensed Atlas
   financial advisor instead of giving investment advice.
4. **Bank policy grounding** — ask "What's the overdraft fee?" or "What's
   the APY on savings?" and confirm the answer matches `bank_policies.py`
   exactly ($35 overdraft fee, 4.15% APY).
5. **Tone under stress** — try "I can't afford my rent this month" and
   confirm the response is empathetic, not judgmental, and offers a
   concrete next step.
