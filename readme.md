# Multi Agent Personal Assistant

A multi-agent productivity assistant that consolidates Gmail, Google Calendar, weather, and web search behind one conversational interface. Built with [AutoGen AgentChat](https://microsoft.github.io/autogen/) (`SelectorGroupChat`) to orchestrate four specialized agents — instead of one monolithic assistant trying to do everything, each service gets its own agent with its own tools and system prompt, and a selector LLM picks the single agent best suited to handle each request. Exposed via a FastAPI server with a small built-in web chat UI, so it's usable straight from a browser with no external platform to configure. All credentials live in a git-ignored `.env` file — nothing is hardcoded in the source.

**Stack:** Python 3.12 — [AutoGen AgentChat / Core / Ext](https://microsoft.github.io/autogen/) for agent orchestration, [Groq](https://groq.com/) (`openai/gpt-oss-20b` by default) via `autogen_ext`'s `OpenAIChatCompletionClient` pointed at Groq's OpenAI-compatible API, [FastAPI](https://fastapi.tiangolo.com/) serving a plain HTML/CSS/vanilla-JS chat page (no frontend framework or build step), Google Gmail/Calendar APIs (OAuth2, via `google-api-python-client` and LangChain's `GmailToolkit` for email tools), [Tavily](https://tavily.com/) for web search, and [Open-Meteo](https://open-meteo.com/) + [Nominatim](https://nominatim.org/) (OpenStreetMap) for weather — both free, no API key required.

## Quick Start

For anyone who just wants the commands — see the Detailed Setup Guide below for explanations and troubleshooting.

```bash
# 1. Clone and enter the project
git clone https://github.com/enescaglarr/Multi-Agent-Personal-Assistant.git
cd Multi-Agent-Personal-Assistant

# 2. Set up the environment
python3.12 -m venv vn_autogen
source vn_autogen/bin/activate      # Windows: vn_autogen\Scripts\activate
pip install -r requirements.txt

# 3. Configure credentials
cp .env.example .env
# open .env and fill in GROQ_API_KEY + TAVILY_SEARCH_KEY (see guides below)

# 4. Add Google OAuth credentials
# download your OAuth client as credentials.json into the project root (see guide below)

# 5. Run the server
python app.py
# or: uvicorn app:app --host 0.0.0.0 --port 8000
```

Then open **http://localhost:8000** in a browser and start chatting. On first request that touches Gmail/Calendar, a browser window opens for the Google OAuth consent flow; it saves `token.json` so this only happens once. You can also skip the web UI entirely and call `PersonalAssistantOrchestrator.process_request(...)` directly (see `source/personal_agents.py`'s `__main__` block for a working example).

## Detailed Setup Guide

### 1. Install prerequisites

| Tool | Check if installed | Install if missing |
|---|---|---|
| Python 3.12 | `python3 --version` | [python.org/downloads](https://www.python.org/downloads/) |

A Google Cloud project (Gmail + Calendar APIs), a Groq API key, and a Tavily API key are also required, but those are credentials, not local installs — see the dedicated guides below.

### 2. Clone the repository

```bash
git clone https://github.com/enescaglarr/Multi-Agent-Personal-Assistant.git
cd Multi-Agent-Personal-Assistant
```

### 3. Create the virtual environment

```bash
python3.12 -m venv vn_autogen
source vn_autogen/bin/activate      # Windows: vn_autogen\Scripts\activate
pip install -r requirements.txt
```

### 4. Configure credentials via `.env`

This project reads all credentials from environment variables — nothing is hardcoded in the source.

```bash
cp .env.example .env
```

Then fill in `.env`:

| Variable | What it is | Where to get it |
|---|---|---|
| `GROQ_API_KEY` | Your Groq API key | console.groq.com → API Keys — see **Groq API Setup Guide** below |
| `GROQ_MODEL` | Model name (default `openai/gpt-oss-20b`) | Optional — Groq's model lineup changes over time (older Llama chat models like `llama-3.3-70b-versatile` have since been deprecated); confirm what's currently active on your account via `GET https://api.groq.com/openai/v1/models` or [console.groq.com/docs/models](https://console.groq.com/docs/models) before picking one, and check free-tier limits at [console.groq.com/settings/limits](https://console.groq.com/settings/limits) |
| `GROQ_BASE_URL` | Groq's OpenAI-compatible endpoint | Preset in `.env.example`, no need to change |
| `TAVILY_SEARCH_KEY` | Your Tavily search API key | See **Tavily API Setup Guide** below |
| `DEFAULT_TIMEZONE` | Timezone used for all date/time resolution | Defaults to `Asia/Kolkata`; change to your own, e.g. `Europe/Istanbul` |

`.env` is gitignored and loaded automatically by `source/configurations.py` via `python-dotenv` — never commit it.

### 5. Google Workspace credentials (Gmail + Calendar)

1. Create/select a project in [Google Cloud Console](https://console.cloud.google.com/), enable the **Gmail API** and **Google Calendar API**.
2. Under **APIs & Services → OAuth consent screen**, add your own Google account under **Audience → Test users**. Without this, sign-in fails with `Error 403: access_denied` ("has not completed the Google verification process") — the app stays in Testing mode (fine for personal use), but Google only allows explicitly-added test users to authorize it.
3. Create an OAuth 2.0 Client ID (Desktop app type) under **Credentials**.
4. Download it and save it as `credentials.json` in the project root — this matches `GOOGLE_CREDENTIALS_FILE` in `.env`.
5. On first run, a browser window opens for consent; you may see a "Google hasn't verified this app" warning first (expected for Testing-mode apps requesting Gmail/Calendar scopes) — click **Advanced → Go to \<app name\> (unsafe)** to proceed, since it's your own app. `token.json` is created automatically afterwards (`source/google_utils.py` handles refresh transparently after that).

### 6. Run it

```bash
python app.py
# or: uvicorn app:app --host 0.0.0.0 --port 8000
```

Exposes the chat UI at `GET /` (served from `static/index.html`) and the API it talks to at `POST /api/chat`.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'source'` | Wrong invocation style | Run scripts (`app.py`, `python -m source.personal_agents`, etc.) from the project root, not from inside `source/` |
| Google OAuth browser flow keeps re-opening every run | `token.json` isn't being written/found, or scopes changed | Check `GOOGLE_TOKEN_FILE` path in `.env`/`source/configurations.py`, delete `token.json` and re-auth once if you changed `GOOGLE_SCOPES` |
| `invalid_grant` / OAuth errors | `credentials.json` is stale, wrong OAuth client type, or consent screen misconfigured | Recreate the OAuth client as a **Desktop app** type in Google Cloud Console; re-download `credentials.json` |
| `Error 403: access_denied` — "has not completed the Google verification process" | Your Google account isn't added as a test user on the OAuth consent screen (apps in Testing mode only allow explicitly-approved testers) | Google Cloud Console → **APIs & Services → OAuth consent screen → Audience → Test users → Add users**, add the exact Google account you're signing in with |
| Blank page / 404 at `http://localhost:8000` | `static/` directory missing or not mounted | Confirm `static/index.html`, `static/style.css`, and `static/app.js` exist next to `app.py`; the `StaticFiles` mount in `app.py` serves them from `/static` |
| Browser shows "Error: request failed (500)" | An unhandled exception in `PersonalAssistantOrchestrator.process_request` | Check server logs / `logs/personal_assistant.log` for the actual exception |
| `429` rate limit errors from Groq | Free-tier RPM/RPD cap hit — a burst of questions can still add up, even with `SelectorGroupChat`'s lighter per-turn call count | Wait a few seconds and retry; check your current limits at [console.groq.com/settings/limits](https://console.groq.com/settings/limits) — the orchestrator surfaces the error back as `"Error: ..."` rather than retrying automatically |
| `404 model_not_found` — "The model \<x\> does not exist or you do not have access to it" | `GROQ_MODEL` in `.env` names a model Groq has deprecated/rotated out | List currently-active models with `curl https://api.groq.com/openai/v1/models -H "Authorization: Bearer $GROQ_API_KEY"`, pick a general-purpose one (e.g. `openai/gpt-oss-20b`), update `GROQ_MODEL`, restart the server |
| Tavily search returns "No search results found" | Bad/expired `TAVILY_SEARCH_KEY`, or empty query | Verify the key and quota on the Tavily dashboard |
| Weather tool fails with "Could not find location" | Nominatim couldn't geocode the given city string | Try a more specific location string, or pass `"lat,lon"` directly (both weather tools accept it) |
| `insert_event` / `delete_event` returns a format error | The pipe-separated (`\|`) input string didn't match the expected field count | Match the exact format documented in each tool's docstring in `source/calendar_tools.py` — the LLM constructs this string itself, so a malformed field usually means the prompt needs a clearer example |

## Groq API Setup Guide

**Step 1 — Create a Groq account**
Visit [console.groq.com](https://console.groq.com/) and sign in (no credit card required for the free tier).

**Step 2 — Generate an API key**
Go to **API Keys** → **Create API Key**. Copy and save it — this is your `GROQ_API_KEY`.

**Step 3 — Understand usage and limits**
Groq's free tier is generous enough for iterative development, though exact limits change over time and by model — check yours anytime at [console.groq.com/settings/limits](https://console.groq.com/settings/limits). Groq also rotates its model lineup periodically (older models get deprecated) — if `GROQ_MODEL` starts returning `404 model_not_found`, list what's actually active on your key with `curl https://api.groq.com/openai/v1/models -H "Authorization: Bearer $GROQ_API_KEY"` and pick a current general-purpose/tool-calling model (Groq itself recommends the `openai/gpt-oss` family — `120b` for more capability, `20b` for speed). This project talks to Groq through its OpenAI-compatible endpoint (`GROQ_BASE_URL`), reusing `autogen_ext`'s `OpenAIChatCompletionClient` rather than a provider-specific client — that's why `create_model_client()` in `source/personal_agents.py` passes an explicit `model_info` dict (these models aren't something AutoGen recognizes natively, so their capabilities have to be declared by hand).

## Tavily API Setup Guide

1. Sign up at [Tavily](https://tavily.com/).
2. Get your API key from the dashboard.
3. Add it to `.env` as `TAVILY_SEARCH_KEY`. Free tier is sufficient for development/testing.

## Web UI

`app.py` serves a small single-page chat interface — no separate front-end project, no build step, just static HTML/CSS/JS served by FastAPI itself:

- `GET /` returns `static/index.html`.
- `GET /static/*` serves `style.css` / `app.js` (mounted via `StaticFiles`).
- `POST /api/chat` accepts `{"message": "..."}` and returns `{"response": "..."}`, calling `PersonalAssistantOrchestrator.process_request()` directly and awaiting the full multi-agent run before responding.

Open `http://localhost:8000`, type a request, and the page shows a typing indicator until the response comes back. Example requests to try:
```
What's the weather in Delhi?
Schedule a meeting tomorrow at 3 PM
Search for the latest news about artificial intelligence
Find my emails from john@example.com
```

Conversation history lives only in the browser tab (rendered client-side in `static/app.js`); nothing is persisted server-side between requests, and each request is handled as an independent `process_request()` call.

## How the System Works

```
1. Request arrives     Browser POSTs {"message": "..."} to /api/chat, or a direct process_request() call
2. Agent selection     SelectorGroupChat's selector (Groq) makes one LLM call to pick the single agent
                        that should handle the request, based on each AssistantAgent's `description`
3. Tool execution      The chosen agent calls its FunctionTool-wrapped methods (Gmail/Calendar/
                        Open-Meteo/Tavily) and replies -- reflect_on_tool_use is off, so the tool's own
                        output becomes the agent's reply directly, with no extra LLM pass over it
4. Stop                The run is capped at exactly one agent turn (MaxMessageTermination(2), OR'd with
                        TextMentionTermination("TERMINATE") as a redundant early-exit): that agent's reply
                        is final, full stop -- no second agent gets a chance to overwrite it
5. Delivery            app.py awaits the run, strips any trailing TERMINATE marker, and returns
                        {"response": "..."}; static/app.js renders it as a chat bubble in the page
```

Each of the four agents is deliberately narrow — an `AssistantAgent` with its own `system_message` (see `source/prompts.py`) and its own tool set (see `source/*_tools.py`), rather than one agent with every tool attached. This is what makes agent selection reliable: the selector routes by reading each agent's `description` (e.g. *"Only pick me when the user explicitly wants email help"*), so a weather question never accidentally triggers a Gmail search.

**Why the run is capped at one agent turn:** the selector picks a single agent up front based on its `description`, and that agent's reply is treated as final -- the run doesn't loop back for a second opinion. `MaxMessageTermination(2)` (OR'd with `TextMentionTermination("TERMINATE")` as a redundant early-exit) enforces this directly, rather than depending on the agent reliably emitting a literal `TERMINATE` marker to signal it's done -- open-weight models don't always follow that instruction consistently, so treating the first turn as authoritative is more robust than trusting a second LLM call's self-reported completion. This also keeps latency and LLM-call-count low: typically just 2 calls total per request (one to select the agent, one for that agent's own tool-use turn). The trade-off: genuinely multi-step requests (e.g. "check my calendar, then email me a summary") aren't handled in one message -- ask as separate follow-up messages instead, each routed to the right single agent.

Design notes on tool-calling, worth knowing if you're extending this:
- **`reflect_on_tool_use=False`** on every agent: a tool's own output becomes the agent's reply directly, with no extra LLM pass to "reflect" on it first. This keeps per-request LLM-call-count low, and avoids a Groq/`gpt-oss` quirk where that reflection pass can call a tool even when explicitly told not to (`tool_choice=none`), which the API then rejects outright with `400 Tool choice is none, but model called a tool`.
- **No `get_current_datetime` tool**: since each agent's turn is capped at one tool-calling round (no reflection to chain a second, dependent tool call), a tool that exists only to feed its result into a *later* tool call doesn't fit well here. Instead, the current date/time (in `DEFAULT_TIMEZONE`) is formatted directly into every agent's `system_message` at agent-creation time (`_get_current_datetime_str()` in `source/personal_agents.py`) -- each agent already knows today's date from its own prompt, no tool call needed. (Worth knowing: this is computed once when the agent is created, not per-request, so on a server left running for a very long time without restart, "today" could drift stale -- restart periodically if deploying this beyond local/personal use.)
- **Response formatting lives in each agent's own `system_message`** (e.g. `search_system_prompt` says to always cite sources) rather than in a separate team-level synthesis step -- one fewer LLM call per request.

Two design choices worth calling out:
- **Draft-first email**: the email agent's system prompt only allows `GmailSendMessage` when the user explicitly asks to send; otherwise it drafts. This is a deliberate safety rail against an LLM sending an email nobody asked to send.
- **No API keys for weather**: Open-Meteo + Nominatim were chosen specifically because neither requires signup or a key, unlike OpenWeatherMap-style providers — one less credential to manage for a feature that doesn't need paid-tier accuracy.

## Project Structure

```
AiPersonalAssistant
├─ .env.example              # credential template — copy to .env
├─ .env                      # your actual secrets (git-ignored)
├─ .gitignore
├─ LICENSE                   # MIT
├─ app.py                    # FastAPI server: serves the web UI + POST /api/chat
├─ static
│  ├─ index.html               # chat page markup
│  ├─ style.css                # chat UI styling (light/dark aware)
│  └─ app.js                   # fetch() calls to /api/chat, renders chat bubbles
├─ requirements.txt
├─ readme.md
├─ credentials.json          # Google OAuth client (you create this, git-ignored)
├─ token.json                # OAuth token (auto-generated, git-ignored)
├─ source
│  ├─ __init__.py
│  ├─ personal_agents.py       # Orchestrator: creates the 4 agents + SelectorGroupChat, routes requests
│  ├─ configurations.py        # Loads .env into a single Config object
│  ├─ prompts.py                # System prompts for all 4 agents
│  ├─ email_tools.py            # Gmail tools: LangChain GmailToolkit (draft/send) + custom search_emails/get_email (clean formatting, see Agent Capabilities below)
│  ├─ calendar_tools.py         # Google Calendar tools (list/create/insert/delete events, Meet links)
│  ├─ weather_tools.py          # Open-Meteo + Nominatim tools (current/forecast/rain probability)
│  ├─ search_tools.py           # Tavily web_search / research_search tools
│  ├─ google_utils.py           # Shared OAuth2 credential + service builder for Gmail/Calendar
│  └─ log_records.py            # Logger setup (console + logs/personal_assistant.log)
└─ logs/                      # Created at runtime
```

## Agent Capabilities

- **Email Agent** — drafts and sends Gmail messages via LangChain's `GmailToolkit`; only sends when explicitly told to. Searching and reading use two custom tools (`source/email_tools.py`) instead of LangChain's own `GmailSearch`/`GmailGetMessage`, both of which return full raw email bodies (quoted threads, signatures, footers) unsuitable for a chat reply -- `search_emails` calls the Gmail API with `format="metadata"` and returns just subject/sender/date/a short preview/message id per result; `get_email` fetches one email's full content by id, decoding the MIME payload down to its plain-text body (truncated past 3000 chars).
- **Calendar Agent** — list calendars/events, create Meet-enabled events (including recurring ones via RRULE), delete events by title match with single-or-series scope; cautious about destructive/bulk actions per its system prompt.
- **Weather Agent** — current conditions, hourly/daily/tomorrow forecasts, and rain-probability windows (today/evening/tonight/tomorrow) for any city, geocoded on the fly.
- **Search Agent** — Tavily-backed `web_search` (quick, 5 results) and `research_search` (advanced depth, 10 results), always citing sources per its own system prompt.

## Development

**Adding a new tool:** add a method to the relevant `*Tools` class, wrap it in `as_function_tools()`, and mention it in that agent's system prompt in `source/prompts.py`.

**Adding a new agent:** create a `create_<x>_agent()` function in `source/personal_agents.py` following the existing pattern, add it to `PersonalAssistantOrchestrator._initialize_agents()`'s `agent_list`, and give it a specific `description` so the orchestrator's routing stays reliable.

**Testing individual components:**
```bash
python -m source.search_tools
python -m source.weather_tools
python -m source.calendar_tools
python -m source.personal_agents
```

## Logging

All operations log to both the console and `logs/personal_assistant.log`, with timestamps and levels (`source/log_records.py`). The orchestrator additionally logs each agent's intermediate "thought" messages per request, so a multi-agent run's full reasoning trail is recoverable from the log file, not just the final answer.

## What This Project Demonstrates

1. Multi-agent system architecture — how several specialized AI agents collaborate on a task instead of one monolithic model handling everything.
2. Tool integration — how agents call external APIs/functions to act beyond pure language generation.
3. AutoGen's agent ecosystem — `AssistantAgent` and `SelectorGroupChat`, and how routing works via agent `description`s rather than hardcoded if/else logic.
4. Async tool design — every tool method is `async`, so the four agents' tool sets are built concurrently (`asyncio.gather` in `_initialize_agents()`) instead of sequentially.
5. Prompt-driven behavior constraints — safety rails like "draft, don't send unless asked" or "be cautious with destructive calendar actions" live entirely in `source/prompts.py`, not in code.
6. OAuth2 in practice — a full Google Workspace auth flow (initial consent, token persistence, silent refresh) shared across two different services (Gmail, Calendar).
7. Provider-agnostic LLM integration — every agent and tool is built against AutoGen's own abstractions rather than a specific provider's SDK, so `create_model_client()` in `source/personal_agents.py` is the only place that knows it's talking to Groq specifically.
8. A thin, framework-free web front-end — `app.py` + `static/` is plain FastAPI and vanilla HTML/CSS/JS with no build step, calling `PersonalAssistantOrchestrator.process_request(text)` and rendering whatever string comes back.
