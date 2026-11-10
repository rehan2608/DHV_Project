"""
NIRF Natural-Language Query and Visualization Playground (Pre-Phase 8).
Connects the complete Phase 3–7 pipeline:
Gemma Query Interpretation -> Validated QueryPlan -> Phase 4 QueryExecutor ->
Phase 5 RAG Retrieval -> Phase 6 Response Generation & Deterministic Verification ->
Phase 7 Plotly Visualization & Table Fallback.
"""

import sys
from pathlib import Path
import time
import json
import logging
import uuid

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from src.llm.gemma_client import get_gemma_client, GemmaClientError
from src.query_engine.parser import get_query_parser, QueryParsingError
from src.query_engine.validator import get_query_validator
from src.query_engine.intent_router import get_intent_router
from src.query_engine.schemas import ConversationContext, QueryPlan, QueryValidationResult
from src.execution.executor import QueryExecutor
from src.execution.result_schema import ExecutionResult
from src.rag.retriever import RAGRetriever
from src.response.generator import ResponseGenerator
from src.visualization.visualization_service import get_visualization_service
from src.conversation.session_manager import get_session_manager

# Configure page layout
st.set_page_config(
    page_title="NIRF Query Playground — Phase 3–7 Pipeline",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling (Botanical Sage / Pastel Mint Aesthetic with High Contrast Accessibility)
st.markdown("""
<style>
    /* App Canvas & Typography */
    .stApp {
        background: linear-gradient(135deg, #8BC3BA 0%, #7CB4A6 100%);
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Header & Branding */
    .kicker-badge {
        display: inline-block;
        background: rgba(255, 255, 255, 0.22);
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 1.2px;
        text-transform: uppercase;
        padding: 5px 14px;
        border-radius: 9999px;
        border: 1px solid rgba(255, 255, 255, 0.38);
        margin-bottom: 0.6rem;
    }
    .main-title {
        font-size: 2.7rem;
        font-weight: 800;
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
        letter-spacing: -0.5px;
        margin-bottom: 0.3rem;
        text-shadow: 0 2px 10px rgba(25, 60, 52, 0.15);
    }
    .main-subtitle {
        font-size: 1.08rem;
        color: #E8F5F1 !important;
        -webkit-text-fill-color: #E8F5F1 !important;
        line-height: 1.5;
        margin-bottom: 1.6rem;
    }

    /* Section Headings on Canvas */
    .main h2, .main h3, .main h4,
    h2, h3, h4 {
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
        text-shadow: 0 1px 3px rgba(18, 45, 38, 0.25);
    }

    /* Input Form: Crystal Clear Dark Text & Visible Cursor on Pure White */
    div[data-testid="stTextArea"] label p {
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
        font-size: 1.05rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.2px !important;
    }
    textarea, input,
    div[data-testid="stTextArea"] textarea,
    div[data-baseweb="textarea"] textarea,
    div[data-testid="stTextInput"] input,
    div[data-baseweb="input"] input {
        background-color: #FFFFFF !important;
        border-radius: 16px !important;
        color: #14352D !important;
        -webkit-text-fill-color: #14352D !important;
        caret-color: #14352D !important; /* High contrast visible typing cursor */
        border: 2px solid rgba(255, 255, 255, 0.7) !important;
        box-shadow: 0 6px 24px rgba(27, 63, 54, 0.12) !important;
        font-size: 1.05rem !important;
        font-weight: 500 !important;
        padding: 14px 16px !important;
    }
    textarea:focus, input:focus,
    div[data-testid="stTextArea"] textarea:focus,
    div[data-baseweb="textarea"] textarea:focus {
        border-color: #275A4E !important;
        outline: none !important;
        box-shadow: 0 0 0 3px rgba(39, 90, 78, 0.25) !important;
    }
    textarea::placeholder, input::placeholder {
        color: #6C968D !important;
        -webkit-text-fill-color: #6C968D !important;
    }
    
    /* "SHOP NOW" Style Pure White Pill Buttons */
    div[data-testid="stFormSubmitButton"] > button {
        background-color: #FFFFFF !important;
        color: #275A4E !important;
        -webkit-text-fill-color: #275A4E !important;
        border: none !important;
        border-radius: 9999px !important;
        padding: 10px 34px !important;
        font-size: 1rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.5px !important;
        box-shadow: 0 6px 20px rgba(20, 50, 43, 0.22) !important;
        transition: all 0.25s ease-in-out !important;
    }
    div[data-testid="stFormSubmitButton"] > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 10px 28px rgba(20, 50, 43, 0.32) !important;
        background-color: #F8FCFB !important;
        color: #1B453B !important;
        -webkit-text-fill-color: #1B453B !important;
    }

    /* User Query Banner */
    .user-query-banner {
        background: rgba(255, 255, 255, 0.25);
        border: 1px solid rgba(255, 255, 255, 0.45);
        border-radius: 14px;
        padding: 12px 20px;
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
        font-size: 1.08rem;
        margin: 16px 0;
    }
    .user-query-banner * {
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
    }

    /* Assistant Response Card */
    .assistant-card {
        background-color: #FFFFFF !important;
        border-radius: 20px;
        padding: 26px 30px;
        margin: 12px 0 24px 0;
        box-shadow: 0 8px 30px rgba(20, 50, 43, 0.12);
        color: #14352D !important;
        -webkit-text-fill-color: #14352D !important;
        font-size: 1.04rem;
        line-height: 1.65;
    }
    .assistant-card * {
        color: #14352D !important;
        -webkit-text-fill-color: #14352D !important;
    }
    .assistant-card h1, .assistant-card h2, .assistant-card h3, .assistant-card h4 {
        color: #275A4E !important;
        -webkit-text-fill-color: #275A4E !important;
        text-shadow: none !important;
        margin-top: 14px;
        margin-bottom: 8px;
    }
    .assistant-card strong, .assistant-card b {
        color: #0E2822 !important;
        -webkit-text-fill-color: #0E2822 !important;
    }

    /* Metrics: High-Contrast Pure White Card with Dark Forest Text */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF !important;
        border-radius: 16px !important;
        padding: 16px 20px !important;
        box-shadow: 0 6px 20px rgba(20, 50, 43, 0.12) !important;
        border: 1px solid rgba(255, 255, 255, 0.9) !important;
    }
    div[data-testid="stMetric"] * {
        color: #14352D !important;
        -webkit-text-fill-color: #14352D !important;
    }
    div[data-testid="stMetricLabel"],
    div[data-testid="stMetricLabel"] *,
    label[data-testid="stMetricLabel"],
    label[data-testid="stMetricLabel"] * {
        color: #2B574C !important;
        -webkit-text-fill-color: #2B574C !important;
        font-weight: 700 !important;
        font-size: 0.82rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.6px !important;
    }
    div[data-testid="stMetricValue"],
    div[data-testid="stMetricValue"] * {
        color: #0E2822 !important;
        -webkit-text-fill-color: #0E2822 !important;
        font-weight: 800 !important;
        font-size: 1.85rem !important;
    }

    /* Plotly Visualizations Card & High-Contrast SVG Typography */
    div[data-testid="stPlotlyChart"] {
        background-color: #FFFFFF;
        border-radius: 18px;
        padding: 12px;
        box-shadow: 0 8px 30px rgba(27, 63, 54, 0.12);
        margin-bottom: 16px;
    }
    div[data-testid="stPlotlyChart"] text,
    div[data-testid="stPlotlyChart"] .legendtext,
    div[data-testid="stPlotlyChart"] .infolayer text,
    div[data-testid="stPlotlyChart"] .g-gtitle,
    div[data-testid="stPlotlyChart"] .xtick text,
    div[data-testid="stPlotlyChart"] .ytick text,
    div[data-testid="stPlotlyChart"] .textpoint text {
        fill: #14352D !important;
        color: #14352D !important;
        font-weight: 600 !important;
    }

    /* Tables & Expanders */
    div[data-testid="stDataFrame"] {
        background-color: #FFFFFF !important;
        border-radius: 14px !important;
        padding: 8px !important;
        box-shadow: 0 4px 20px rgba(27, 63, 54, 0.08) !important;
    }
    div[data-testid="stDataFrame"] * {
        color: #14352D !important;
        -webkit-text-fill-color: #14352D !important;
    }
    div[data-testid="stExpander"] {
        background-color: #FFFFFF !important;
        border-radius: 14px !important;
        border: none !important;
        box-shadow: 0 4px 16px rgba(27, 63, 54, 0.08) !important;
        color: #14352D !important;
        margin-bottom: 12px !important;
    }
    div[data-testid="stExpander"] * {
        color: #14352D !important;
        -webkit-text-fill-color: #14352D !important;
    }
    div[data-testid="stExpander"] summary {
        color: #14352D !important;
        -webkit-text-fill-color: #14352D !important;
        font-weight: 600 !important;
    }

    /* Sidebar Customization */
    [data-testid="stSidebar"] {
        background-color: #76A89B !important;
        border-right: 1px solid rgba(255, 255, 255, 0.22) !important;
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] h4 {
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
    }
    /* Only plain prose paragraphs directly in sidebar markdown, NOT inside buttons or dropdowns */
    [data-testid="stSidebar"] .stMarkdown > div > p,
    [data-testid="stSidebar"] caption {
        color: #E8F5F1 !important;
        -webkit-text-fill-color: #E8F5F1 !important;
    }

    /* Sidebar Buttons: Bold Dark Forest Text on Pure White Pill */
    [data-testid="stSidebar"] div.stButton > button {
        background-color: #FFFFFF !important;
        color: #1A473D !important;
        -webkit-text-fill-color: #1A473D !important;
        border: none !important;
        border-radius: 9999px !important;
        font-weight: 700 !important;
        padding: 9px 22px !important;
        box-shadow: 0 4px 16px rgba(20, 50, 43, 0.18) !important;
        transition: all 0.2s ease-in-out !important;
    }
    [data-testid="stSidebar"] div.stButton > button * {
        color: #1A473D !important;
        -webkit-text-fill-color: #1A473D !important;
        font-weight: 700 !important;
    }
    [data-testid="stSidebar"] div.stButton > button:hover {
        background-color: #F8FCFB !important;
        box-shadow: 0 6px 20px rgba(20, 50, 43, 0.26) !important;
        transform: translateY(-1px);
    }
    [data-testid="stSidebar"] div.stButton > button:hover * {
        color: #0F3028 !important;
        -webkit-text-fill-color: #0F3028 !important;
    }

    /* Sidebar Selectbox: Clean White Box with Dark Text & No White Artifacts */
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] label p {
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        margin-bottom: 6px !important;
    }
    [data-testid="stSidebar"] div[data-baseweb="select"] {
        background-color: transparent !important;
    }
    [data-testid="stSidebar"] div[data-baseweb="select"] > div {
        background-color: #FFFFFF !important;
        border-radius: 12px !important;
        border: none !important;
        box-shadow: 0 4px 14px rgba(20, 50, 43, 0.12) !important;
    }
    [data-testid="stSidebar"] div[data-baseweb="select"] * {
        color: #14352D !important;
        -webkit-text-fill-color: #14352D !important;
        font-weight: 600 !important;
    }
    [data-testid="stSidebar"] div[data-baseweb="popover"] * {
        color: #14352D !important;
        -webkit-text-fill-color: #14352D !important;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def initialize_pipeline_components():
    """Initializes and caches all core pipeline modules."""
    parser = get_query_parser()
    validator = get_query_validator()
    executor = QueryExecutor()
    generator = ResponseGenerator()
    vis_service = get_visualization_service()
    retriever = RAGRetriever()
    intent_router = get_intent_router()
    return parser, validator, executor, generator, vis_service, retriever, intent_router


parser, validator, executor, generator, vis_service, retriever, intent_router = initialize_pipeline_components()
session_mgr = get_session_manager()

# Session State & SQLite Initialization (Phase 8)
if "session_id" not in st.session_state:
    st.session_state["session_id"] = session_mgr.start_new_session(title="New Conversation")

if "context" not in st.session_state:
    st.session_state["context"] = session_mgr.get_active_context(st.session_state["session_id"])

if "last_query" not in st.session_state:
    st.session_state["last_query"] = ""

if "last_result" not in st.session_state:
    st.session_state["last_result"] = None

if "query_input_text" not in st.session_state:
    st.session_state["query_input_text"] = ""


# =============================================================================
# Sidebar: Pipeline Controls & System Status
# =============================================================================

st.sidebar.markdown("## 💬 NIRF Assistant")
st.sidebar.markdown(
    '<span class="pipeline-badge">Conversational AI & Memory Engine</span>',
    unsafe_allow_html=True,
)

# Health Status
gemma_client = get_gemma_client()
try:
    health = gemma_client.check_health()
    st.sidebar.success(f"🟢 LLM Engine: {health.get('model')} ({health.get('latency_seconds')}s)")
except Exception as e:
    st.sidebar.error(f"🔴 Gemma Offline: {e}")

# Session Management (Phase 8: SQLite Persistence)
st.sidebar.markdown("### 🗂️ Conversation Sessions")
if st.sidebar.button("➕ New Chat", use_container_width=True):
    new_sid = session_mgr.start_new_session(title="New Conversation")
    st.session_state["session_id"] = new_sid
    st.session_state["context"] = ConversationContext()
    st.session_state["last_result"] = None
    st.session_state["query_input_text"] = ""
    st.rerun()

all_sessions = session_mgr.list_all_sessions()
if all_sessions:
    sess_dict = {s.session_id: f"{s.title} ({s.turn_count} turns)" for s in all_sessions}
    curr_id = st.session_state["session_id"]
    curr_idx = list(sess_dict.keys()).index(curr_id) if curr_id in sess_dict else 0
    selected_sess = st.sidebar.selectbox(
        "Saved Chats (SQLite)",
        options=list(sess_dict.keys()),
        index=curr_idx,
        format_func=lambda x: sess_dict.get(x, x),
    )
    if selected_sess != st.session_state["session_id"]:
        st.session_state["session_id"] = selected_sess
        st.session_state["context"] = session_mgr.get_active_context(selected_sess)
        st.session_state["last_result"] = None
        st.rerun()

# Display active context snapshot if filters are active
active_ctx = session_mgr.get_active_context(st.session_state["session_id"])
if active_ctx.previous_category or active_ctx.previous_year or active_ctx.previous_institution_names:
    st.sidebar.markdown("#### 🧠 Active Memory Filters")
    if active_ctx.previous_category:
        st.sidebar.caption(f"• **Category:** `{active_ctx.previous_category}`")
    if active_ctx.previous_year:
        st.sidebar.caption(f"• **Year:** `{active_ctx.previous_year}`")
    if active_ctx.previous_institution_names:
        st.sidebar.caption(f"• **Institutions:** {', '.join(active_ctx.previous_institution_names[:3])}")

if st.sidebar.button("🧹 Reset Active Context", use_container_width=True):
    session_mgr.reset_context(st.session_state["session_id"])
    st.session_state["context"] = ConversationContext()
    st.sidebar.info("Conversation context reset.")
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 Dataset Scope")
st.sidebar.caption("NIRF 2017–2025 | All Categories & Parameters | Interactive Maps & Plotly Charts")


# =============================================================================
# Main Application Pipeline Execution
# =============================================================================

st.markdown('<div class="kicker-badge">🌿 GROW GOOD VIBES • NIRF INTELLIGENCE</div>', unsafe_allow_html=True)
st.markdown('<div class="main-title">NIRF Conversational Assistant</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="main-subtitle">Ask any question in natural language about Indian institutional rankings (2017–2025), comparisons, trends, or NIRF parameters. Answers are strictly grounded in authoritative data and documentation.</div>',
    unsafe_allow_html=True,
)

# Question Input Form
with st.form(key="query_form", clear_on_submit=False):
    user_question = st.text_area(
        label="Ask your question:",
        value=st.session_state["query_input_text"],
        placeholder="e.g. Compare IIT Bombay and IIT Delhi in Engineering for 2025, or how have institutional categories evolved from 2017 to 2025?",
        height=90,
    )
    submit_button = st.form_submit_button("✨ EXPLORE ANALYTICS", type="primary")

if submit_button and user_question.strip():
    q = user_question.strip()
    st.session_state["last_query"] = q

    with st.spinner("Processing query through Phases 3–7 pipeline..."):
        t0_total = time.time()

        # Step 0: General Conversational Intent Routing
        intent_res = intent_router.route_intent(q, st.session_state["context"])
        if intent_res.is_conversational:
            session_mgr.record_turn(
                session_id=st.session_state["session_id"],
                user_query=q,
                assistant_response=intent_res.response_text or "",
                intent=intent_res.intent,
            )
            st.session_state["last_result"] = {
                "question": q,
                "is_conversational": True,
                "is_knowledge": False,
                "intent": intent_res.intent,
                "conversational_response": intent_res.response_text,
                "parsed_plan": None,
                "val_result": None,
                "exec_res": None,
                "rag_res": None,
                "generated_response": None,
                "vis_results": [],
                "latency_total": round(time.time() - t0_total, 3),
                "is_blocked": False,
            }
        elif intent_res.intent == "DOCUMENTATION_QUERY":
            # Knowledge query: grounded RAG retrieval and verified response generation
            t0_rag = time.time()
            if not retriever.is_ready():
                retriever.build_or_refresh_index()
            rag_res = retriever.retrieve(q, top_k=3)
            rag_duration = round(time.time() - t0_rag, 2)

            t0_gen = time.time()
            generated_response = None
            try:
                generated_response = generator.generate_response(
                    original_question=q,
                    query_id=f"doc_{uuid.uuid4().hex[:6]}",
                    execution_result=None,
                    retrieval_result=rag_res,
                )
            except Exception as ge:
                logging.error("RAG response generation error: %s", ge)

            ans_text = generated_response.answer if generated_response else "Methodology information retrieved."
            session_mgr.record_turn(
                session_id=st.session_state["session_id"],
                user_query=q,
                assistant_response=ans_text,
                intent="NIRF_KNOWLEDGE",
                generated_response=generated_response,
            )

            st.session_state["last_result"] = {
                "question": q,
                "is_conversational": False,
                "is_knowledge": True,
                "intent": "NIRF_KNOWLEDGE",
                "conversational_response": None,
                "parsed_plan": None,
                "val_result": None,
                "exec_res": None,
                "rag_res": rag_res,
                "generated_response": generated_response,
                "vis_results": [],
                "latency_total": round(time.time() - t0_total, 2),
                "is_blocked": False,
            }
        else:
            # Step 1: Phase 3 Query Parsing with Gemma
            try:
                t0_parse = time.time()
                current_context = st.session_state["context"]
                parsed_plan = parser.parse(q, conversation_context=current_context)
                parse_duration = round(time.time() - t0_parse, 2)
            except GemmaClientError as ge:
                st.error(f"❌ **Gemma Connection Error:** {ge}. Ensure Ollama is running and accessible.")
                st.stop()
            except QueryParsingError as qpe:
                st.error(f"❌ **Query Parsing Failure:** {qpe}")
                st.stop()
            except Exception as e:
                st.error(f"❌ **Unexpected Parsing Failure:** {e}")
                st.stop()

            # Step 2: Phase 3 Independent Query Validation
            val_result: QueryValidationResult = validator.validate(parsed_plan)
            valid_plan = val_result.validated_plan or parsed_plan

            # Check for immediate clarification or unsupported status
            if not val_result.is_valid or val_result.status in ["CLARIFICATION_REQUIRED", "UNSUPPORTED", "INVALID"]:
                st.session_state["last_result"] = {
                    "question": q,
                    "is_conversational": False,
                    "parsed_plan": parsed_plan,
                    "val_result": val_result,
                    "exec_res": None,
                    "generated_response": None,
                    "vis_results": [],
                    "latency_total": round(time.time() - t0_total, 2),
                    "is_blocked": True,
                }
            else:
                # Step 3: Phase 4 Deterministic Execution Engine
                t0_exec = time.time()
                exec_res: ExecutionResult = executor.execute(valid_plan)
                exec_duration = round(time.time() - t0_exec, 2)

                # Step 4: Phase 5 RAG Retrieval (when applicable)
                rag_res = None
                if valid_plan.semantic_retrieval_needed or "mean" in q.lower() or "define" in q.lower() or "what is" in q.lower():
                    try:
                        if not retriever.is_ready():
                            retriever.build_or_refresh_index()
                        rag_res = retriever.retrieve(q, top_k=2)
                    except Exception as re:
                        logging.warning("RAG retrieval failed: %s", re)

                # Step 5: Phase 6 Response Generation & Verification
                t0_gen = time.time()
                generated_response = None
                try:
                    generated_response = generator.generate_response(
                        original_question=q,
                        query_id=valid_plan.query_id,
                        execution_result=exec_res,
                        retrieval_result=rag_res,
                    )
                except Exception as ge:
                    logging.error("Response generation error: %s", ge)

                # Step 6: Phase 7 Plotly Visualization Service
                t0_vis = time.time()
                pref_chart = valid_plan.visualization.preferred_chart_type if valid_plan and valid_plan.visualization else None
                vis_results = vis_service.visualize_execution_result(exec_res, user_query=q, chart_preference=pref_chart)
                vis_duration = round(time.time() - t0_vis, 2)

                # Step 7: Record Turn in SQLite & Update Context State (Phase 8)
                ans_text = generated_response.answer if generated_response else "Analytical execution completed."
                session_mgr.record_turn(
                    session_id=st.session_state["session_id"],
                    user_query=q,
                    assistant_response=ans_text,
                    intent="ANALYTICAL_QUERY",
                    query_plan=valid_plan,
                    execution_result=exec_res,
                    generated_response=generated_response,
                )
                st.session_state["context"] = session_mgr.get_active_context(st.session_state["session_id"])

                latency_total = round(time.time() - t0_total, 2)

                st.session_state["last_result"] = {
                    "question": q,
                    "is_conversational": False,
                    "parsed_plan": parsed_plan,
                    "val_result": val_result,
                    "exec_res": exec_res,
                    "rag_res": rag_res,
                    "generated_response": generated_response,
                    "vis_results": vis_results,
                    "latency_total": latency_total,
                    "is_blocked": False,
                }


# =============================================================================
# Display Stored Results
# =============================================================================

res_data = st.session_state.get("last_result")

if res_data:
    q_disp = res_data["question"]
    plan_disp: QueryPlan = res_data["parsed_plan"]
    val_disp: QueryValidationResult = res_data["val_result"]
    exec_disp: ExecutionResult = res_data.get("exec_res")
    gen_disp = res_data.get("generated_response")
    vis_list = res_data.get("vis_results", [])
    total_time = res_data.get("latency_total", 0.0)

    # Top Status Banner
    st.markdown("---")
    st.markdown(f'<div class="user-query-banner"><b>Question:</b> <i>"{q_disp}"</i></div>', unsafe_allow_html=True)

    if res_data.get("is_conversational"):
        st.markdown(f'<div class="assistant-card"><h4 style="margin-top:0;">💬 Assistant</h4>{res_data["conversational_response"]}</div>', unsafe_allow_html=True)
        st.caption(f"⚡ Response time: {total_time}s | Intent: {res_data['intent']}")

    elif res_data.get("is_knowledge"):
        st.markdown("### 💬 Assistant")
        if gen_disp:
            st.markdown(f'<div class="assistant-card">{gen_disp.answer}</div>', unsafe_allow_html=True)
            if gen_disp.citations:
                st.markdown("#### 📖 Approved Methodology Citations")
                for cite in gen_disp.citations:
                    title = getattr(cite, "document_title", None) or getattr(cite, "source_file", None) or "NIRF Methodology Document"
                    page = getattr(cite, "page_number", "N/A")
                    st.caption(f"• **[{cite.citation_id}]** *{title}* (p. {page})")
        else:
            st.info("No narrative explanation generated.")
        st.caption(f"⚡ Response time: {total_time}s | Grounded in official NIRF documentation via vector RAG.")

    elif res_data.get("is_blocked"):
        st.warning(f"⚠️ **Validation Notice ({val_disp.status}):** Query cannot be executed directly.")
        if plan_disp.clarification_message:
            st.info(f"💬 **Clarification Needed:** {plan_disp.clarification_message}")
        if plan_disp.unsupported_reason:
            st.error(f"🚫 **Unsupported Reason:** {plan_disp.unsupported_reason}")
        if val_disp.errors:
            for err in val_disp.errors:
                st.error(f"• {err}")

    else:
        # Metrics banner
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            st.metric("Status", exec_disp.status if exec_disp else "UNKNOWN")
        with col_m2:
            st.metric("Response Time", f"{total_time}s")
        with col_m3:
            st.metric("Query Type", plan_disp.query_type)
        with col_m4:
            st.metric("Visualizations", len([v for v in vis_list if v.has_chart]))

        # SECTION A: Final Answer (Phase 6)
        st.markdown("### 💬 Assistant Answer")
        if gen_disp:
            st.markdown(f'<div class="assistant-card">{gen_disp.answer}</div>', unsafe_allow_html=True)

            # Warning badges if present in response
            if gen_disp.warnings:
                for w in gen_disp.warnings:
                    st.warning(f"⚠️ **Data Warning:** {w}")
        else:
            st.info("Direct analytical execution completed; no natural-language narrative generated.")

        # SECTION B: Interactive Visualizations (Phase 7 & 8)
        st.markdown("### 📊 Interactive Visualizations")
        if vis_list:
            for idx, vr in enumerate(vis_list, 1):
                chart_name = vr.chart_spec.title if vr.chart_spec else vr.function_name
                st.markdown(f"**Visualization {idx}: {chart_name}** — *{vr.explanation or ''}*")
                if vr.warnings:
                    for w in vr.warnings:
                        st.warning(f"⚠️ {w}")

                if vr.has_chart and vr.figure is not None:
                    st.plotly_chart(vr.figure, use_container_width=True, theme=None)
                elif vr.status == "FALLBACK_TABLE":
                    st.info("ℹ️ Table representation automatically selected (lookup format or small sample size).")
                    if vr.table_data:
                        st.dataframe(pd.DataFrame(vr.table_data), use_container_width=True, hide_index=True)
        else:
            st.info("No visualization generated for this question.")

        # SECTION C: Underlying Data Table
        st.markdown("### 📋 Section C: Underlying Analytical Data")
        has_table_data = False
        for idx, vr in enumerate(vis_list, 1):
            if vr.table_data:
                has_table_data = True
                st.markdown(f"**Table for {vr.function_name}:**")
                df_op = pd.DataFrame(vr.table_data)
                st.dataframe(df_op, use_container_width=True, hide_index=True)

                csv_op = vr.to_csv()
                if csv_op:
                    st.download_button(
                        label=f"📥 Download {vr.function_name} CSV",
                        data=csv_op,
                        file_name=f"{vr.operation_id}_{vr.function_name}.csv",
                        mime="text/csv",
                        key=f"csv_down_{vr.operation_id}_{idx}",
                    )
        if not has_table_data:
            st.caption("No tabular records available.")

        # SECTION D: Query Interpretation (Phase 3)
        with st.expander("🔍 Section D: Gemma Query Interpretation (Phase 3 QueryPlan)"):
            st.markdown(f"**Query ID:** `{plan_disp.query_id}` | **Intent:** {plan_disp.analytical_intent}")
            st.markdown(f"**Semantic Retrieval Needed:** {plan_disp.semantic_retrieval_needed}")
            st.markdown(f"**Operations Count:** {len(plan_disp.operations)}")
            for idx, op in enumerate(plan_disp.operations, 1):
                st.markdown(
                    f"- **Op {idx}:** `{op.function_name}` | Category: `{op.category}` | Year: `{op.year or op.start_year}` | "
                    f"Institutions: `{op.institution_names}` | States: `{op.states}` | Parameters: `{op.parameters}`"
                )
            st.json(plan_disp.model_dump())

        # SECTION E: Execution Details (Phase 4)
        with st.expander("⚙️ Section E: Execution Engine Details (Phase 4 ExecutionResult)"):
            if exec_disp:
                st.markdown(f"**Execution ID:** `{exec_disp.execution_id}` | **Status:** `{exec_disp.status}`")
                st.markdown(f"**Warnings Count:** {len(exec_disp.warnings)}")
                if exec_disp.warnings:
                    for w in exec_disp.warnings:
                        st.markdown(f"- ⚠️ {w}")
                st.json(exec_disp.to_dict())
            else:
                st.caption("Execution did not run.")

        # SECTION F: Verification & Retrieval Details (Phase 5 & 6)
        with st.expander("🛡️ Section F: Claim Verification & Retrieval Grounding (Phase 5 & 6)"):
            if gen_disp:
                vs = gen_disp.verification_summary
                st.markdown(
                    f"**Verification Status:** Total Claims: `{vs.total_claims}` | "
                    f"Verified: `{vs.verified_claims}` | Contradicted: `{vs.contradicted_claims}` | "
                    f"Unverified: `{vs.unverified_claims}`"
                )
                if gen_disp.numerical_claims:
                    claims_df = pd.DataFrame([
                        {
                            "Claim Text": c.claim_text,
                            "Type": c.claim_type,
                            "Status": c.verification_status,
                            "Claimed Value": c.claimed_value,
                            "Actual Value": c.actual_value,
                            "Notes": c.verification_notes,
                        }
                        for c in gen_disp.numerical_claims
                    ])
                    st.dataframe(claims_df, use_container_width=True, hide_index=True)
                if gen_disp.citations:
                    st.markdown("**Citations:**")
                    for cite in gen_disp.citations:
                        st.markdown(f"- `[{cite.citation_id}]` {cite.document_title} ({cite.source_file})")
            else:
                st.caption("No claim verification output available.")

    # Session Conversation History (Phase 8: SQLite Persistence)
    turns = session_mgr.get_history(st.session_state["session_id"])
    if len(turns) > 1:
        st.markdown("---")
        with st.expander(f"💬 Conversation History ({len(turns)} turns recorded in SQLite)", expanded=False):
            for t in turns[:-1]:
                st.markdown(f"**User (Turn {t.turn_index}):** *\"{t.user_query}\"*")
                st.markdown(f"**Assistant:** {t.assistant_response}")
                st.divider()

