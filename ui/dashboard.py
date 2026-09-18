"""Streamlit Dashboard UI for Autonomous Financial Fraud Investigation."""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from typing import Dict, Any, Optional

from agent.state import InvestigationState, AgentStep
from .visualizations import render_network_graph, render_risk_gauge

def apply_custom_styles():
    """Inject sleek dark-fintech styling for a high-impact presentation."""
    st.markdown("""
    <style>
    /* Global App Styling */
    .stApp {
        background-color: #0B0F17;
        color: #E2E8F0;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Card Container */
    .investigation-card {
        background: #131B2A;
        border: 1px solid #1E293B;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
        margin-bottom: 20px;
    }

    /* Activity Step Badges */
    .agent-step-card {
        background: #111827;
        border-left: 4px solid #38BDF8;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 10px;
    }

    .tool-badge {
        background-color: #1E293B;
        color: #38BDF8;
        padding: 3px 8px;
        border-radius: 6px;
        font-weight: 600;
        font-family: monospace;
        font-size: 0.85rem;
    }

    .obs-badge {
        color: #10B981;
        font-weight: 500;
    }

    /* Risk Score Highlights */
    .risk-pill-critical {
        background: rgba(239, 68, 68, 0.2);
        color: #EF4444;
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: 700;
        border: 1px solid #EF4444;
    }
    .risk-pill-low {
        background: rgba(16, 185, 129, 0.2);
        color: #10B981;
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: 700;
        border: 1px solid #10B981;
    }
    </style>
    """, unsafe_allow_html=True)

def render_dashboard(state: Optional[InvestigationState], on_investigate_callback):
    """Render the primary Streamlit interface."""
    apply_custom_styles()

    # -------------------------------------------------------------------------
    # HEADER SECTION
    # -------------------------------------------------------------------------
    col_head, col_badge = st.columns([3, 1])
    with col_head:
        st.title("🛡️ Autonomous Financial Fraud Investigation")
        st.caption("AI-powered network discovery for financial investigations | Network-level anomaly traversal")
    with col_badge:
        st.markdown("""
        <div style="text-align: right; padding-top: 15px;">
            <span style="background: #1E293B; border: 1px solid #38BDF8; color: #38BDF8; padding: 6px 14px; border-radius: 20px; font-size: 0.85rem; font-weight: 600;">
                ⚡ PS-3 Prototype
            </span>
        </div>
        """, unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # INVESTIGATION CONTROLS & DEMO PRESETS
    # -------------------------------------------------------------------------
    st.markdown("### 🔍 Initiate Autonomous Investigation")
    
    # Preset quick-selector
    preset_cols = st.columns(4)
    preset_tx = None
    if preset_cols[0].button("🚩 Seed TX1001 (Mule Ring)", use_container_width=True):
        preset_tx = "TX1001"
    if preset_cols[1].button("🔄 Seed TX2001 (Circular Wash)", use_container_width=True):
        preset_tx = "TX2001"
    if preset_cols[2].button("🎭 Seed TX3001 (Synthetic ID)", use_container_width=True):
        preset_tx = "TX3001"
    if preset_cols[3].button("✅ Seed TX9001 (Clean Baseline)", use_container_width=True):
        preset_tx = "TX9001"

    input_cols = st.columns([3, 1, 1])
    default_input = preset_tx or (state.seed_transaction_id if state else "TX1001")
    target_tx = input_cols[0].text_input("Enter Target Transaction ID:", value=default_input, key="tx_input_field")
    
    provider_choice = input_cols[1].selectbox(
        "Agent Engine:",
        ["Autonomous Heuristic (Zero API Key)", "Groq LLM", "OpenAI LLM"],
        index=0
    )
    
    start_btn = input_cols[2].button("🚀 INVESTIGATE", type="primary", use_container_width=True)

    if start_btn or preset_tx:
        active_id = preset_tx if preset_tx else target_tx
        provider_key = "autonomous" if "Autonomous" in provider_choice else ("groq" if "Groq" in provider_choice else "openai")
        on_investigate_callback(active_id, provider_key)
        return

    # If no investigation has run yet, show welcome instructions
    if not state:
        st.info("👆 Select a planted demo scenario above (e.g. **TX1001**) or enter any transaction ID and click **INVESTIGATE** to watch the AI agent autonomously discover fraud networks.")
        return

    # -------------------------------------------------------------------------
    # STATUS & KPI METRIC CARDS
    # -------------------------------------------------------------------------
    st.markdown("---")
    m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
    
    m_col1.metric("Investigation Status", state.status, delta="Autonomous ReAct" if state.status == "COMPLETED" else None)
    m_col2.metric("Entities Discovered", len(state.discovered_nodes), delta=f"{len(state.get_accounts())} Accounts")
    m_col3.metric("Relationships Mapped", len(state.discovered_edges), delta="Multi-relational")
    
    risk_score = state.risk_evaluation.get("prototype_risk_score", 0)
    risk_sev = state.risk_evaluation.get("risk_severity", "Low")
    m_col4.metric("Prototype Risk Score", f"{risk_score}/100", delta=risk_sev, delta_color="inverse" if risk_score > 50 else "normal")
    m_col5.metric("Suspicious Indicators", len(state.risk_evaluation.get("indicators", [])), delta=f"{len(state.action_history)} Steps")

    # -------------------------------------------------------------------------
    # MAIN WORKSPACE TABS
    # -------------------------------------------------------------------------
    tab_graph, tab_activity, tab_report, tab_evidence, tab_check = st.tabs([
        "🌐 Discovered Network Graph",
        "🤖 Agent Activity Log",
        "📄 Investigation Report",
        "🔬 Risk Indicators & Evidence",
        "📋 Human Investigator Checklist"
    ])

    # -------------------------------------------------------------------------
    # TAB 1: INTERACTIVE NETWORK GRAPH
    # -------------------------------------------------------------------------
    with tab_graph:
        col_g, col_gauge = st.columns([3, 1])
        with col_g:
            st.markdown("#### 🕸️ Discovered Multi-Entity Fraud Network")
            st.caption("Drag nodes to inspect clustering. Hover to view metadata. Node colors indicate entity roles.")
            
            # Entity Legend
            st.markdown("""
            <div style="display: flex; gap: 12px; margin-bottom: 8px; font-size: 0.82rem;">
                <span style="color: #F59E0B;">◆ Seed Transaction</span>
                <span style="color: #3B82F6;">● Account</span>
                <span style="color: #10B981;">■ Customer</span>
                <span style="color: #EF4444;">▲ Device</span>
                <span style="color: #8B5CF6;">⬢ Merchant</span>
                <span style="color: #EC4899;">★ Beneficiary Aggregator</span>
            </div>
            """, unsafe_allow_html=True)

            graph_html = render_network_graph(state.get_nodes_list(), state.discovered_edges)
            components.html(graph_html, height=560)

        with col_gauge:
            st.markdown("#### 🎯 Risk Gauge")
            gauge_fig = render_risk_gauge(risk_score, risk_sev)
            st.plotly_chart(gauge_fig, use_container_width=True)

            st.markdown("##### 📌 Key Topology Stats")
            topo = state.graph_topology
            st.markdown(f"- **Total Nodes**: `{topo.get('total_nodes', 0)}`")
            st.markdown(f"- **Total Edges**: `{topo.get('total_edges', 0)}`")
            st.markdown(f"- **Graph Density**: `{topo.get('graph_density', 0.0)}`")
            if topo.get("aggregator_node"):
                st.error(f"🚨 **Aggregator**: `{topo['aggregator_node']['node']}` ({topo['aggregator_node']['incoming_count']} incoming)")
            if topo.get("circular_cycles"):
                st.warning(f"🔄 **Wash Cycle**: `{' -> '.join(topo['circular_cycles'][0])}`")

    # -------------------------------------------------------------------------
    # TAB 2: AGENT ACTIVITY STREAM
    # -------------------------------------------------------------------------
    with tab_activity:
        st.markdown("#### 🧠 Autonomous Agent Activity & Reasoning Trail")
        st.caption("Visualizing genuine step-by-step agent autonomy: Observe → Plan → Tool Execution → Reason.")

        for step in state.action_history:
            with st.container():
                st.markdown(f"""
                <div class="agent-step-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <span style="font-weight: 700; color: #F8FAFC;">Step {step.step_number} • <span class="tool-badge">{step.tool_name}()</span></span>
                        <span style="font-size: 0.8rem; color: #94A3B8;">{step.timestamp}</span>
                    </div>
                    <div style="font-style: italic; color: #CBD5E1; margin-bottom: 6px;">
                        💭 <b>Reasoning</b>: {step.thought}
                    </div>
                    <div class="obs-badge">
                        ✓ <b>Observation</b>: {step.observation_summary}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                with st.expander(f"View Raw Tool Payload ({step.tool_name})", expanded=False):
                    st.json({"arguments": step.tool_args, "result": step.raw_result})

    # -------------------------------------------------------------------------
    # TAB 3: INVESTIGATION REPORT
    # -------------------------------------------------------------------------
    with tab_report:
        st.markdown("#### 📋 Explainable Investigation Dossier")
        st.download_button(
            label="📥 Download Investigation Report (Markdown)",
            data=state.final_report,
            file_name=f"investigation_report_{state.seed_transaction_id}.md",
            mime="text/markdown"
        )
        st.markdown(state.final_report)

    # -------------------------------------------------------------------------
    # TAB 4: RISK INDICATORS & EVIDENCE BREAKDOWN
    # -------------------------------------------------------------------------
    with tab_evidence:
        st.markdown("#### ⚖️ Transparent Risk Indicator Scoring")
        st.caption("Deterministic point attribution. Factual evidence strictly verified from underlying synthetic data.")

        indicators = state.risk_evaluation.get("indicators", [])
        if indicators:
            df_ind = pd.DataFrame([
                {
                    "Severity": ind.get("severity", "Medium"),
                    "Indicator": ind["indicator"],
                    "Risk Points": f"+{ind.get('points', 0)}",
                    "Concrete Evidence": ind["evidence"]
                }
                for ind in indicators
            ])
            st.dataframe(df_ind, use_container_width=True, hide_index=True)
        else:
            st.success("No suspicious risk indicators detected. Account shows routine behavior.")

        st.markdown("#### ⛓️ Reconstructed Evidence Lineage")
        for i, step in enumerate(state.risk_evaluation.get("evidence_chain", []), 1):
            st.markdown(f"**{i}.** {step}")

        st.markdown("#### 🗃️ Discovered Entity Ledger")
        e_col1, e_col2 = st.columns(2)
        with e_col1:
            st.markdown("##### Discovered Accounts")
            acc_list = [{"Account ID": n["id"], **n.get("properties", {})} for n in state.get_nodes_list() if n["type"] == "Account"]
            if acc_list:
                st.dataframe(pd.DataFrame(acc_list), use_container_width=True, hide_index=True)
        with e_col2:
            st.markdown("##### Discovered Hardware Devices & Merchants")
            dev_merch = [{"ID": n["id"], "Type": n["type"], **n.get("properties", {})} for n in state.get_nodes_list() if n["type"] in ["Device", "Merchant", "Beneficiary"]]
            if dev_merch:
                st.dataframe(pd.DataFrame(dev_merch), use_container_width=True, hide_index=True)

    # -------------------------------------------------------------------------
    # TAB 5: INVESTIGATOR CHECKLIST
    # -------------------------------------------------------------------------
    with tab_check:
        st.markdown("#### 👮 Human Investigator Action Plan")
        st.caption("Prioritized operational steps recommended for compliance officers and fraud operations.")

        for rec in state.recommendations:
            with st.container():
                p = rec["priority"]
                color = "#EF4444" if "P1" in p else ("#F97316" if "P2" in p else "#3B82F6")
                st.markdown(f"""
                <div style="background: #111827; border-left: 4px solid {color}; border-radius: 8px; padding: 14px; margin-bottom: 12px;">
                    <div style="font-weight: 700; color: {color}; font-size: 0.95rem;">{rec['priority']} - {rec['action']}</div>
                    <div style="color: #E2E8F0; margin-top: 6px; font-size: 0.9rem;">{rec['details']}</div>
                </div>
                """, unsafe_allow_html=True)
