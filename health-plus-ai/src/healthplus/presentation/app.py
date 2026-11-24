"""Streamlit chat portal — the human face of the HealthPlus RAG stack.

WHY this file looks the way it does:

Streamlit re-executes this entire script on every user interaction (a
"rerun"). Anything that must survive between reruns therefore lives in one
of two places:

- ``st.cache_resource`` for heavy, process-wide singletons. The ChatService
  keeps conversation memory *in the object itself*, and building it loads
  the embedding model and constructs the Claude client — so it must be
  built exactly once and reused, never rebuilt per rerun.
- ``st.session_state`` for per-browser-tab state: the visible chat log
  (display only — the service records its own memory for the LLM) and the
  conversation id that keys that service-side memory.

Every failure path the backend documents (missing API key, Claude outage,
bad query, bad PDF) is caught and shown as a friendly message. A user of
this app should never see a Python traceback.
"""

from __future__ import annotations

import html
import json
import linecache
import re
import logging
import os
import sys
import uuid
from pathlib import Path

# Streamlit Cloud updates code in place without restarting the process.
# st.cache_resource reads each cached function's source via inspect, which
# uses linecache; a stale cached copy of the old file makes it read the
# wrong lines (tokenize.TokenError). Forget this file's cached source on
# every run so it is re-read from disk; checkcache() alone is not enough
# because entries registered for exec'd scripts carry no mtime to compare.
for _path in {__file__, str(Path(__file__).resolve())}:
    linecache.cache.pop(_path, None)
linecache.checkcache()

# Hosted platforms (e.g. Streamlit Cloud) install requirements.txt but not
# this project as a package, so make `src/` importable when it isn't already.
_SRC_DIR = Path(__file__).resolve().parents[2]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

import streamlit as st  # noqa: E402
import streamlit.components.v1 as components  # noqa: E402

# API keys can come from `.env` (local) or Streamlit secrets (Streamlit
# Cloud: app Settings -> Secrets). Settings only reads environment
# variables, so copy any secrets-provided keys into the environment before
# get_settings() is first called. Real environment variables win.
_SECRET_KEYS = ("OPENROUTER_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY")
# Short, value-free description of what st.secrets held, shown only in the
# "key not set" error to help diagnose deployment setup. Never key values.
_secrets_status = "not checked"
try:
    _secret_names = sorted(st.secrets.keys())
    _secrets_status = (
        f"loaded; top-level names: {', '.join(_secret_names)}"
        if _secret_names else "loaded but empty"
    )
    for _key in _SECRET_KEYS:
        if not os.environ.get(_key) and _key in st.secrets:
            os.environ[_key] = str(st.secrets[_key]).strip()
except Exception as _exc:  # no secrets.toml (normal for local runs using .env)
    _secrets_status = f"not available ({type(_exc).__name__})"

from healthplus.application import KnowledgeBaseService, build_chat_service
from healthplus.config import get_settings
from healthplus.core.exceptions import ConfigurationError, HealthPlusError, LLMError
from healthplus.core.logging import configure_logging
from healthplus.core.privacy import redact_personal_data
from healthplus.knowledge_base.models import DocumentCategory

logger = logging.getLogger(__name__)

# Streamlit Cloud applies edited Secrets without restarting the process
# (and copies them into os.environ itself), but get_settings() is cached
# from the first run. If the environment now has a key the cached settings
# lack, rebuild them so the new key is used without a reboot.
if any(
    os.environ.get(_key) and getattr(get_settings(), _key.lower()) is None
    for _key in _SECRET_KEYS
):
    get_settings.cache_clear()

# Sentinel label for "no category filter" in the sidebar selectbox.
ALL_CATEGORIES = "All categories"

# LLM backends shown in the sidebar, in display order (first = default).
# Keys are the provider names build_chat_service() understands.
PROVIDERS = {
    "openrouter": {
        # e.g. "inclusionai/ling-3.2-flash:free" -> "OpenRouter · ling-3.2-flash:free"
        "label": f"OpenRouter · {get_settings().openrouter_model.split('/')[-1]}",
        "env_key": "OPENROUTER_API_KEY",
    },
    "claude": {"label": "Claude (Anthropic)", "env_key": "ANTHROPIC_API_KEY"},
    "openai": {"label": "ChatGPT (OpenAI)", "env_key": "OPENAI_API_KEY"},
}

DISCLAIMER ="Informational assistant for hospital operations — not medical advice."

# set_page_config must be the first Streamlit call in the script.
st.set_page_config(
    page_title="HealthPlus AI",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="auto",
)

# ---------------------------------------------------------------------------
# Global look — styles.css (theme) + background.js (animated particle
# network, card spotlight, count-up numbers). The script guards itself so
# Streamlit reruns never start a second animation loop.
# ---------------------------------------------------------------------------

_HERE = Path(__file__).parent
st.markdown(
    f"<style>{(_HERE / 'styles.css').read_text(encoding='utf-8')}</style>",
    unsafe_allow_html=True,
)
# A zero-height component iframe (same origin) copies background.js into
# the main page as a <script>, so it runs in the app's own window and keeps
# animating even if Streamlit later re-mounts this iframe.
_BG_JS = json.dumps((_HERE / "background.js").read_text(encoding="utf-8"))
components.html(
    "<script>(function(){var d=window.parent.document;"
    "if(d.getElementById('hp-bg-script'))return;"
    "var s=d.createElement('script');s.id='hp-bg-script';"
    f"s.textContent={_BG_JS};d.head.appendChild(s);}})();</script>",
    height=0,
)


# ---------------------------------------------------------------------------
# Process-wide singletons (survive reruns via st.cache_resource)
# ---------------------------------------------------------------------------


@st.cache_resource
def _bootstrap() -> None:
    """One-time process setup: runtime directories and logging.

    Wrapped in cache_resource so reruns don't re-configure logging (the
    configure function is idempotent anyway, but there is no reason to pay
    for it on every interaction).
    """
    settings = get_settings()
    settings.ensure_directories()
    configure_logging(level=settings.log_level, log_dir=settings.log_dir)


@st.cache_resource(show_spinner="Opening the knowledge base…")
def _get_knowledge_base() -> KnowledgeBaseService:
    """The KB service used by the sidebar (stats + PDF uploads).

    Deliberately separate from the chat service: uploads and stats only
    need the vector store and embedder, NOT the Claude API key — so the
    sidebar keeps working even when the key is missing. The chat service
    reuses this same instance (see _get_chat_service).

    The embedding model is warmed here, at startup, so the first question
    does not pay its load time.
    """
    kb = KnowledgeBaseService()
    kb.warm_up()
    return kb


@st.cache_resource(show_spinner="Starting the assistant…")
def _get_chat_service(provider: str = "claude"):
    """One ChatService per provider for this process.

    Cached separately per provider value so switching between Claude and
    OpenAI does not rebuild the service each time — just the first switch.
    Raises ConfigurationError if the required API key is missing; Streamlit
    does not cache exceptions, so fixing .env and rerunning recovers cleanly.

    Shares the sidebar's knowledge base rather than opening a second vector
    store and embedding model.
    """
    return build_chat_service(provider=provider, kb=_get_knowledge_base())


_bootstrap()


# ---------------------------------------------------------------------------
# Per-tab state (survives reruns via st.session_state)
# ---------------------------------------------------------------------------

if "messages" not in st.session_state:
    # Display log only. Each entry: {"role": ..., "content": ..., "sources": [...]}.
    # The ChatService keeps its own memory for the LLM — we never feed this back.
    st.session_state["messages"] = []

if "conversation_id" not in st.session_state:
    # Keys the service-side conversation memory. A fresh id = a fresh memory.
    st.session_state["conversation_id"] = uuid.uuid4().hex


def _reset_conversation() -> None:
    """Clear the visible log AND rotate the conversation id.

    Rotating the id matters: the service's memory is keyed by it, so a new
    id means the LLM also starts from a blank history — clearing only the
    display would leave the model still 'remembering' the old chat.

    The old conversation is also deleted server-side, for every provider's
    cached service, so cleared chats are not kept in memory.
    """
    old_id = st.session_state.get("conversation_id")
    if old_id:
        settings = get_settings()
        for provider, info in PROVIDERS.items():
            # Skip providers without a key: they were never used, and
            # building them would just import a heavy SDK for nothing.
            if getattr(settings, info["env_key"].lower(), None) is None:
                continue
            try:
                _get_chat_service(provider).forget(old_id)
            except HealthPlusError:
                pass
    st.session_state["messages"] = []
    st.session_state["conversation_id"] = uuid.uuid4().hex


def _render_sources(sources: list[dict]) -> None:
    """Render retrieval citations as styled source cards inside an expander.

    Takes plain dicts (SearchResult.model_dump()) so the same function works
    for both the just-streamed answer and messages replayed from the log.
    """
    if not sources:
        return
    with st.expander(f"📄 Sources ({len(sources)})", expanded=False):
        for i, src in enumerate(sources, start=1):
            # Keep the citation number the answer used ([n]), even when only
            # some sources are shown.
            number = src.get("citation", i)
            snippet = src["text"][:220].strip()
            if len(src["text"]) > 220:
                snippet += "…"
            # Document text and file names end up inside raw HTML: escape
            # them so a crafted PDF cannot inject markup into the page.
            snippet = html.escape(snippet)
            title = html.escape(str(src["source"]))
            cat_label = html.escape(src["category"].replace("_", " ").title())
            st.markdown(
                f"""
                <div class="hp-source-card">
                    <div class="hp-source-title">[{number}] {title}</div>
                    <div class="hp-source-meta">
                        <span class="hp-badge">📄 Page {src['page_number']}</span>
                        <span class="hp-badge hp-badge-cat">{cat_label}</span>
                        <span class="hp-badge hp-badge-score">Score {src['score']:.2f}</span>
                    </div>
                    <div class="hp-source-snippet">{snippet}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Sidebar: knowledge-base stats, category filter, conversation & upload tools
# ---------------------------------------------------------------------------

# The sidebar depends only on the KB service (no Claude key needed), so we
# build it BEFORE attempting the chat service — a missing API key must not
# take down stats or uploads.
knowledge_base: KnowledgeBaseService | None = None
try:
    knowledge_base = _get_knowledge_base()
except HealthPlusError as exc:
    st.sidebar.error(f"Knowledge base unavailable: {exc}")

with st.sidebar:
    # Brand strip. Knowledge-base stats live in the main overview panel.
    st.markdown(
        '<div class="hp-side-brand">'
        '<div class="hp-mark">+</div>'
        '<div><b>HealthPlus AI</b><small>Diagnostic Intelligence</small></div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Chat settings ─────────────────────────────────────────────────
    st.markdown('<div class="hp-sidebar-label">Chat Settings</div>', unsafe_allow_html=True)

    # OpenRouter is listed first so it is the default: its free model lets
    # the app run without paid Anthropic/OpenAI keys.
    selected_provider = st.radio(
        "LLM provider",
        options=list(PROVIDERS),
        format_func=lambda key: PROVIDERS[key]["label"],
        help="Switch the language model powering the assistant.",
        label_visibility="collapsed",
    )

    # The filter narrows retrieval, not the LLM: answer(category=...) only
    # searches chunks tagged with the chosen category.
    filter_choice = st.selectbox(
        "Search within category",
        options=[ALL_CATEGORIES] + [c.value for c in DocumentCategory],
        help="Limit retrieval to one document category, or search everything.",
    )
    selected_category: str | None = (
        None if filter_choice == ALL_CATEGORIES else filter_choice
    )

    if st.button("🗑️ Clear conversation", use_container_width=True):
        _reset_conversation()
        st.rerun()

    st.caption(
        "🔒 **Privacy:** don't enter personal details. Phone numbers, emails, "
        "and ID or card numbers are removed automatically before a question "
        "is sent. Chats are not saved — clearing deletes them from memory."
    )

    st.markdown('<hr class="hp-divider">', unsafe_allow_html=True)

    # ── Document upload ───────────────────────────────────────────────
    st.markdown('<div class="hp-sidebar-label">Add a Document</div>', unsafe_allow_html=True)

    # A successful ingest ends in st.rerun() (so the stats above refresh),
    # which would wipe an inline st.success — so the message is parked in
    # session_state and shown on the run AFTER the rerun.
    if "last_ingest_message" in st.session_state:
        st.success(st.session_state.pop("last_ingest_message"))

    if knowledge_base is None:
        st.caption("Uploads are disabled while the knowledge base is unavailable.")
    else:
        uploaded_file = st.file_uploader("PDF document", type=["pdf"], label_visibility="collapsed")
        upload_category = st.selectbox(
            "Document category",
            options=list(DocumentCategory),
            format_func=lambda c: c.value.replace("_", " ").title(),
        )
        if st.button(
            "⬆️ Ingest document",
            type="primary",
            use_container_width=True,
            disabled=uploaded_file is None,
        ):
            try:
                with st.spinner("Ingesting document…"):
                    settings = get_settings()
                    uploads_dir = settings.data_dir / "uploads"
                    uploads_dir.mkdir(parents=True, exist_ok=True)
                    # Persist the upload to disk first: the pipeline's loader
                    # works on paths, and keeping the file gives us a
                    # re-ingestable record of what entered the KB.
                    saved_path = uploads_dir / uploaded_file.name
                    saved_path.write_bytes(uploaded_file.getvalue())
                    report = knowledge_base.ingest_pdf(
                        saved_path, category=upload_category
                    )
                st.session_state["last_ingest_message"] = (
                    f"✅ Ingested {report.source}: {report.pages} pages → "
                    f"{report.chunks} chunks in {report.duration_seconds}s."
                )
                # Rerun so the chunk/category stats at the top reflect the
                # freshly ingested document.
                st.rerun()
            except HealthPlusError as exc:
                # Covers DocumentLoadError and EmptyDocumentError (bad or
                # scanned PDFs) with the pipeline's own explanation.
                st.error(f"Could not ingest {uploaded_file.name}: {exc}")


# ---------------------------------------------------------------------------
# Main area: hero header, history, and the chat loop
# ---------------------------------------------------------------------------

provider_label = PROVIDERS[selected_provider]["label"]

# One-click starter questions on the empty state. Clicking one parks the
# question in session_state; the chat loop below picks it up like typed input.
SUGGESTIONS = [
    "🩺  Which specialists are available this week?",
    "🧪  What does a full blood panel test include?",
    "💳  How much does an MRI scan cost?",
    "📋  What is the patient admission procedure?",
]

category_counts = knowledge_base.category_counts() if knowledge_base else {}
kb_chunks = knowledge_base.chunk_count if knowledge_base else 0
scope_label = (
    "All documents" if selected_category is None
    else selected_category.replace("_", " ").title()
)


def _overview_panel_html() -> str:
    """Glass 'dashboard' card: KB stats plus a bar per category."""
    if category_counts:
        top = max(category_counts.values())
        bars = "".join(
            '<div class="hp-bar">'
            f'<div class="hp-bar-label">{name.replace("_", " ").title()}<em>{count}</em></div>'
            f'<div class="hp-bar-track"><div class="hp-bar-fill" style="--w:{count / top * 100:.0f}%;'
            f'animation-delay:{0.5 + i * 0.12:.2f}s"></div></div>'
            "</div>"
            for i, (name, count) in enumerate(
                sorted(category_counts.items(), key=lambda kv: -kv[1])
            )
        )
    else:
        bars = '<div class="hp-bar-label">No documents yet — upload a PDF from the sidebar.</div>'
    return (
        '<div class="hp-panel hp-rise hp-d4">'
        '<div class="hp-panel-head">'
        '<div class="hp-panel-title">Knowledge overview'
        "<small>Live view of what the assistant can search</small></div>"
        '<div class="hp-dots"><i></i><i></i><i></i></div>'
        "</div>"
        '<div class="hp-grid">'
        '<div class="hp-stats">'
        f'<div class="hp-stat"><b data-count="{kb_chunks}" data-key="chunks">{kb_chunks:,}</b>'
        "<span>Chunks</span></div>"
        f'<div class="hp-stat"><b data-count="{len(category_counts)}" data-key="cats">'
        f"{len(category_counts)}</b><span>Categories</span></div>"
        f'<div class="hp-stat"><b>Top {get_settings().retrieval_top_k}</b><span>Sources / answer</span></div>'
        '<div class="hp-stat hp-stat-wide"><span>Search scope</span>'
        f"<b>{scope_label}</b></div>"
        "</div>"
        f'<div class="hp-bars"><div class="hp-bars-title">Documents by category</div>{bars}</div>'
        "</div></div>"
    )


COMPACT_HEADER = (
    '<div class="hp-compact hp-rise">'
    '<div class="hp-compact-title">Ask HealthPlus <span class="hp-accent">anything.</span></div>'
    f'<span class="hp-pill">Scope · {scope_label}</span>'
    "</div>"
)

# Glass top bar — always visible.
st.markdown(
    '<div class="hp-nav hp-rise">'
    '<div class="hp-brand"><div class="hp-mark">+</div>HealthPlus AI</div>'
    '<div class="hp-nav-right">'
    f'<span class="hp-pill" title="{DISCLAIMER}">⚕ Not medical advice</span>'
    f'<span class="hp-pill hp-pill-live"><i></i>{provider_label}</span>'
    "</div></div>",
    unsafe_allow_html=True,
)

# Intro (hero + overview + starter cards) lives in a placeholder: it is
# swapped for a compact header the moment a conversation starts.
intro_slot = st.empty()
show_intro = not st.session_state["messages"] and "pending_prompt" not in st.session_state
if not show_intro:
    intro_slot.markdown(COMPACT_HEADER, unsafe_allow_html=True)

# Replay the visible history every rerun — Streamlit redraws from scratch.
for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            _render_sources(message.get("sources", []))

if show_intro:
    with intro_slot.container():
        st.markdown(
            '<div class="hp-hero">'
            '<div class="hp-orbit" aria-hidden="true"></div>'
            '<div class="hp-eyebrow hp-rise"><b>✦ RAG</b> AI assistant for hospital teams</div>'
            '<h1 class="hp-rise hp-d1">Hospital answers, instantly.'
            '<span class="hp-serif">Grounded in your documents.</span></h1>'
            '<p class="hp-hero-sub hp-rise hp-d2">Doctors, diagnostic tests, pricing and '
            "policies — answered in seconds, with <b>a cited source behind every reply</b>.</p>"
            "</div>"
            + _overview_panel_html()
            + '<div class="hp-section-title hp-rise hp-d4">Try asking'
            "<span>tap a card or type below</span></div>",
            unsafe_allow_html=True,
        )
        with st.container(key="hp-suggest"):
            for row in (SUGGESTIONS[:2], SUGGESTIONS[2:]):
                cols = st.columns(2, gap="medium")
                for col, text in zip(cols, row):
                    idx = SUGGESTIONS.index(text)
                    if col.button(text, key=f"sg-{idx}", use_container_width=True):
                        st.session_state["pending_prompt"] = text.split("  ", 1)[1]
                        st.rerun()

# The chat service needs an API key for the selected provider. If it is
# missing we stop HERE — after the sidebar — so stats and uploads above
# remain fully usable.
# Popped before the service check so a failed start never leaves a stale
# starter question hiding the welcome screen.
pending_prompt = st.session_state.pop("pending_prompt", None)
try:
    chat_service = _get_chat_service(selected_provider)
except ConfigurationError as exc:
    key_hint = PROVIDERS[selected_provider]["env_key"]
    st.error(
        f"Chat is not available: `{key_hint}` is not set.\n\n"
        f"- **Running locally:** add `{key_hint}=...` to your `.env` file, then restart the app.\n"
        f'- **On Streamlit Cloud:** open your app\'s **Settings → Secrets**, add '
        f'`{key_hint} = "..."` (with quotes), and save. The app restarts by itself.\n\n'
        f"_Diagnostics: Streamlit secrets {_secrets_status}; "
        f"environment variable {'present' if os.environ.get(key_hint) else 'absent'}._"
    )
    st.stop()
except HealthPlusError as exc:
    st.error(f"Chat is not available: {exc}")
    st.stop()

prompt = st.chat_input("Ask about doctors, tests, pricing, policies…") or pending_prompt
if prompt:
    intro_slot.markdown(COMPACT_HEADER, unsafe_allow_html=True)
    # Remove personal identifiers before the question is shown, stored in
    # the chat log, or sent anywhere (the service redacts again, too).
    redaction = redact_personal_data(prompt)
    prompt = redaction.text
    # Echo the user's message immediately so the app feels responsive while
    # retrieval and the Claude call happen below.
    with st.chat_message("user"):
        st.markdown(prompt)
        if redaction.changed:
            st.caption(
                f"🔒 For your privacy, we removed your {' and '.join(redaction.removed)} "
                "before sending this question. The assistant never needs personal details."
            )
    st.session_state["messages"].append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        try:
            answer = chat_service.answer(
                prompt,
                st.session_state["conversation_id"],
                category=selected_category,
            )
        except ValueError as exc:
            # The query processor rejects empty or over-long questions.
            st.warning(str(exc))
        except HealthPlusError as exc:
            st.error(f"Something went wrong answering that: {exc}")
        else:
            source_dicts = [s.model_dump() for s in answer.sources]
            try:
                # write_stream renders tokens as they arrive and returns the
                # full concatenated text once the stream is exhausted.
                full_text = st.write_stream(answer.tokens)
            except LLMError as exc:
                # The Claude call failed mid-flight (network, rate limit,
                # server error). The service intentionally did NOT record
                # this turn in memory, so the conversation stays consistent.
                st.error(f"The assistant could not reply: {exc}")
            else:
                # Show only the sources the answer actually cites: greetings
                # and general-information answers cite nothing, so they get
                # no source list instead of five unrelated documents.
                cited = {int(n) for n in re.findall(r"\[(\d+)\]", full_text)}
                source_dicts = [
                    {**src, "citation": number}
                    for number, src in enumerate(source_dicts, start=1)
                    if number in cited
                ]
                _render_sources(source_dicts)
                st.session_state["messages"].append(
                    {
                        "role": "assistant",
                        "content": full_text,
                        "sources": source_dicts,
                    }
                )
