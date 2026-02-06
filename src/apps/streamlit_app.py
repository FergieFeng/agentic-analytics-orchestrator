"""
Streamlit UI for Agentic Analytics Orchestrator.

A visual interface for running analytics queries and exploring system capabilities.

Usage:
    streamlit run src/apps/streamlit_app.py
"""

import streamlit as st
import sys
import time
from pathlib import Path
from datetime import datetime

# Add project root to path (src/apps/ -> src/ -> project root)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.orchestrator import run_query
from src.config import settings
from src.evaluation import (
    get_query_store,
    score_to_stars,
    collect_feedback_simple,
    format_feedback_summary,
    get_improvement_insights
)

# Page config
st.set_page_config(
    page_title="Agentic Analytics Orchestrator",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Demo scenarios for quick access - aligned with enterprise use cases
DEMO_SCENARIOS = {
    "1. Core Analytics (SQL + RAG)": [
        ("Net Flow Trend", "Show the monthly net flow trend for chequing accounts."),
        ("Event Volume", "How many money movement events occurred each month across all deposit products?"),
        ("Inflow vs Outflow", "Compare monthly inflow and outflow trends for savings accounts."),
    ],
    "2. RAG Knowledge Retrieval": [
        ("Definition (RAG) 🔍", "What does 'money_movement' mean in this dataset?"),
        ("Schema (RAG) 🔍", "Explain the difference between event_type and event_name."),
    ],
    "3. Explanation": [
        ("Trend Interpretation", "Why did net flow decrease for chequing accounts in March?"),
    ],
    "4. Defaults & Ambiguity": [
        ("Ambiguous Request", "Show me the trend of deposit activity."),
        ("Recent Activity", "How has account activity changed recently?"),
    ],
    "5. Privacy (Should Refuse)": [
        ("Customer Ranking ⛔", "Show the top 10 customers by total deposit amount."),
        ("Account Details ⛔", "Give me account_id-level transaction details for March."),
        ("Safe Aggregation ✓", "Which deposit product has the highest average balance?"),
    ],
    "6. Query Safety": [
        ("Large Result ⛔", "Show all events in the dataset."),
    ],
    "7. End-to-End (LangChain)": [
        ("Full Pipeline 🔗", "Show the monthly net flow trend for chequing accounts and explain the key drivers."),
    ],
}


def init_session_state():
    """Initialize session state variables."""
    if "query_history" not in st.session_state:
        st.session_state.query_history = []
    if "current_result" not in st.session_state:
        st.session_state.current_result = None
    if "processing" not in st.session_state:
        st.session_state.processing = False


def render_sidebar():
    """Render the sidebar with demo scenarios."""
    with st.sidebar:
        st.title("🏦 Analytics Orchestrator")
        st.markdown("---")
        
        # Demo mode
        st.subheader("📋 Demo Scenarios")
        
        for category, scenarios in DEMO_SCENARIOS.items():
            with st.expander(category, expanded=False):
                for name, question in scenarios:
                    if st.button(f"▶ {name}", key=f"demo_{name}", use_container_width=True):
                        st.session_state.demo_question = question
                        st.rerun()
        
        st.markdown("---")
        
        # Quick stats
        st.subheader("📊 Quick Stats")
        try:
            store = get_query_store()
            stats = store.get_stats()
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Queries", stats.get("total_queries", 0))
            with col2:
                avg_score = stats.get("avg_self_score")
                st.metric("Avg Score", f"{avg_score:.0f}" if avg_score else "—")
            
            if stats.get("avg_latency_ms"):
                st.caption(f"Avg latency: {stats['avg_latency_ms']:.0f}ms")
        except Exception:
            st.caption("No stats available yet")
        
        st.markdown("---")
        
        # Info
        st.caption("Built with LangChain + LangGraph")
        st.caption("RAG: ChromaDB + OpenAI Embeddings")
        st.caption("Data: Banking Events (Jan-Mar 2024)")


def render_main_input():
    """Render the main query input area."""
    st.header("💬 Ask an Analytics Question")
    
    # Check for demo question
    default_value = st.session_state.get("demo_question", "")
    if default_value:
        del st.session_state.demo_question
    
    col1, col2 = st.columns([5, 1])
    
    with col1:
        question = st.text_input(
            "Question",
            value=default_value,
            placeholder="e.g., What is the total deposit amount by channel?",
            label_visibility="collapsed"
        )
    
    with col2:
        submit = st.button("🔍 Ask", type="primary", use_container_width=True)
    
    return question, submit


def render_pipeline_status(result: dict):
    """Render the agent pipeline status."""
    st.subheader("🔄 Agent Pipeline")
    
    trace = result.get("trace", [])
    
    # Define pipeline stages
    stages = [
        ("scope_guard", "Scope Check", "🛡️"),
        ("router", "Router", "🔀"),
        ("definition_agent", "Definition", "📝"),
        ("sql_agent", "SQL Agent", "🗃️"),
        ("data_quality_agent", "Quality", "✅"),
        ("explanation_agent", "Explanation", "💡"),
    ]
    
    # Check which stages completed
    completed_agents = {t.get("agent") for t in trace if t.get("action") == "completed"}
    
    cols = st.columns(len(stages))
    for i, (agent_key, label, icon) in enumerate(stages):
        with cols[i]:
            if agent_key in completed_agents:
                st.success(f"{icon} {label}")
            elif any(t.get("agent") == agent_key for t in trace):
                st.warning(f"{icon} {label}")
            else:
                st.info(f"⬜ {label}")


def render_results(result: dict):
    """Render the query results."""
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📊 Results")
        
        final_response = result.get("final_response", "No response generated.")
        st.markdown(final_response)
        
        # Show SQL if available
        sql_query = result.get("sql_query")
        if sql_query:
            with st.expander("🗃️ Generated SQL"):
                st.code(sql_query, language="sql")
        
        # Show raw data if available
        sql_result = result.get("sql_result", {})
        if sql_result and sql_result.get("data"):
            with st.expander("📋 Raw Data"):
                import pandas as pd
                df = pd.DataFrame(sql_result["data"])
                st.dataframe(df, use_container_width=True)
    
    with col2:
        st.subheader("🔍 Debug Info")
        
        # Confidence
        self_scores = result.get("self_scores", {})
        overall = self_scores.get("overall", 0)
        confidence = result.get("confidence", "unknown")
        
        st.metric(
            "Confidence",
            f"{score_to_stars(overall)}",
            f"{overall:.0f}/100 ({confidence})"
        )
        
        # Stats
        st.metric("Tokens Used", result.get("total_tokens", 0))
        
        # Score breakdown
        with st.expander("Score Breakdown"):
            for key, value in self_scores.items():
                if key not in ("overall", "confidence", "issues"):
                    st.progress(value / 100, text=f"{key}: {value}")
        
        # Errors
        errors = result.get("errors", [])
        if errors:
            st.error("Errors:")
            for err in errors:
                st.caption(f"• {err}")


def render_feedback(result: dict):
    """Render feedback collection."""
    session_id = result.get("session_id")
    if not session_id:
        return
    
    st.subheader("📝 Rate this Response")
    
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    feedback_given = st.session_state.get(f"feedback_{session_id}")
    
    if not feedback_given:
        with col1:
            if st.button("⭐", use_container_width=True):
                collect_feedback_simple(session_id, 1)
                st.session_state[f"feedback_{session_id}"] = 1
                st.rerun()
        with col2:
            if st.button("⭐⭐", use_container_width=True):
                collect_feedback_simple(session_id, 2)
                st.session_state[f"feedback_{session_id}"] = 2
                st.rerun()
        with col3:
            if st.button("⭐⭐⭐", use_container_width=True):
                collect_feedback_simple(session_id, 3)
                st.session_state[f"feedback_{session_id}"] = 3
                st.rerun()
        with col4:
            if st.button("⭐⭐⭐⭐", use_container_width=True):
                collect_feedback_simple(session_id, 4)
                st.session_state[f"feedback_{session_id}"] = 4
                st.rerun()
        with col5:
            if st.button("⭐⭐⭐⭐⭐", use_container_width=True):
                collect_feedback_simple(session_id, 5)
                st.session_state[f"feedback_{session_id}"] = 5
                st.rerun()
        with col6:
            st.caption("Click to rate")
    else:
        st.success(f"Thanks! Rated: {'⭐' * feedback_given}")


def render_history_tab():
    """Render the history tab."""
    st.header("📜 Query History")
    
    store = get_query_store()
    records = store.get_recent(limit=20)
    
    if not records:
        st.info("No queries yet. Ask some questions to build history!")
        return
    
    for record in records:
        with st.expander(
            f"**{record.question[:60]}{'...' if len(record.question) > 60 else ''}**"
        ):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.caption(f"📅 {record.created_at[:16].replace('T', ' ')}")
            with col2:
                self_score = f"{record.self_score:.0f}/100" if record.self_score else "—"
                st.caption(f"🤖 Self: {self_score}")
            with col3:
                user_score = f"{'⭐' * record.user_score}" if record.user_score else "unrated"
                st.caption(f"👤 User: {user_score}")
            
            if record.sql_query:
                st.code(record.sql_query, language="sql")
            
            st.caption(f"Tokens: {record.total_tokens} | Errors: {record.error_count}")


def render_stats_tab():
    """Render the stats tab."""
    st.header("📊 Performance Statistics")
    
    try:
        store = get_query_store()
        stats = store.get_stats()
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Queries", stats.get("total_queries", 0))
        with col2:
            rated = stats.get("rated_percentage", 0)
            st.metric("Rated", f"{rated:.0f}%")
        with col3:
            avg_self = stats.get("avg_self_score")
            st.metric("Avg Self Score", f"{avg_self:.0f}" if avg_self else "—")
        with col4:
            avg_user = stats.get("avg_user_score")
            st.metric("Avg User Score", f"{avg_user:.1f}/5" if avg_user else "—")
        
        st.markdown("---")
        
        # Performance metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            latency = stats.get("avg_latency_ms")
            st.metric("Avg Latency", f"{latency:.0f}ms" if latency else "—")
        with col2:
            tokens = stats.get("avg_tokens")
            st.metric("Avg Tokens", f"{tokens:.0f}" if tokens else "—")
        with col3:
            error_rate = stats.get("error_rate", 0)
            st.metric("Error Rate", f"{error_rate:.1f}%")
        
        st.markdown("---")
        
        # Insights
        st.subheader("💡 Improvement Insights")
        insights = get_improvement_insights()
        
        if insights:
            for insight in insights:
                st.info(insight)
        else:
            st.success("No issues identified - system performing well!")
            
    except Exception as e:
        st.error(f"Could not load stats: {e}")


def main():
    """Main application entry point."""
    init_session_state()
    
    # Sidebar
    render_sidebar()
    
    # Main content tabs
    tab1, tab2, tab3 = st.tabs(["🔍 Query", "📜 History", "📊 Stats"])
    
    with tab1:
        # Validate settings
        valid, msg = settings.validate()
        if not valid:
            st.error(f"⚠️ Configuration Error: {msg}")
            st.info("Please set up your `.env` file with a valid `OPENAI_API_KEY`")
            st.stop()
        
        # Input
        question, submit = render_main_input()
        
        # Process query
        if submit and question:
            with st.spinner("🔄 Processing query..."):
                start_time = time.time()
                
                try:
                    result = run_query(question, enable_logging=True)
                    elapsed = time.time() - start_time
                    result["elapsed_seconds"] = elapsed
                    
                    st.session_state.current_result = result
                    st.session_state.query_history.append({
                        "question": question,
                        "timestamp": datetime.now().isoformat(),
                        "result": result
                    })
                    
                except Exception as e:
                    st.error(f"Error: {e}")
                    st.session_state.current_result = None
        
        # Display results
        if st.session_state.current_result:
            result = st.session_state.current_result
            
            st.markdown("---")
            render_pipeline_status(result)
            
            st.markdown("---")
            render_results(result)
            
            st.markdown("---")
            render_feedback(result)
    
    with tab2:
        render_history_tab()
    
    with tab3:
        render_stats_tab()


if __name__ == "__main__":
    main()
