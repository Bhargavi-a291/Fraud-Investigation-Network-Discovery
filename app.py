"""Main Streamlit Application Entry Point for Autonomous Financial Fraud Investigation.

Run via:
    streamlit run app.py
"""

import streamlit as st
import time
import os
from dotenv import load_dotenv

# Load environment variables (.env)
load_dotenv()

from tools.db import ensure_database
from agent.agent import FraudInvestigationAgent
from ui.dashboard import render_dashboard

# Ensure database is generated and ready
ensure_database()

st.set_page_config(
    page_title="Autonomous Financial Fraud Investigation",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Session State
if "state" not in st.session_state:
    st.session_state["state"] = None

if "history" not in st.session_state:
    st.session_state["history"] = []

def run_investigation(target_tx_id: str, provider: str = "autonomous"):
    """Trigger autonomous investigation and update UI."""
    target_tx_id = target_tx_id.strip().upper()
    if not target_tx_id:
        st.error("Please provide a valid Transaction ID.")
        return

    progress_bar = st.progress(0, text=f"Initializing autonomous investigation on {target_tx_id}...")
    status_placeholder = st.empty()

    agent = FraudInvestigationAgent(provider=provider)
    
    # Run investigation
    start_time = time.time()
    
    def on_step(step):
        # Callback for real-time progress updates
        pct = min(int((step.step_number / agent.max_steps) * 100), 95)
        progress_bar.progress(pct, text=f"Step {step.step_number}: {step.tool_name}() -> {step.observation_summary[:60]}...")

    with st.spinner(f"Agent actively traversing relationships for {target_tx_id}..."):
        final_state = agent.investigate(target_tx_id, step_callback=on_step)

    elapsed = round(time.time() - start_time, 2)
    progress_bar.progress(100, text=f"Investigation completed in {elapsed}s.")
    time.sleep(0.4)
    progress_bar.empty()

    if final_state.status == "FAILED":
        st.error(final_state.error_message or "Investigation failed.")
    else:
        st.session_state["state"] = final_state
        st.session_state["history"].append({
            "tx_id": target_tx_id,
            "risk_score": final_state.risk_evaluation.get("prototype_risk_score", 0),
            "nodes": len(final_state.discovered_nodes),
            "time": elapsed
        })
        st.rerun()

# -----------------------------------------------------------------------------
# SIDEBAR CONTROLS & BENCHMARK SUITE
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ System Settings")
    st.markdown("**Architecture**: ReAct Autonomous Loop")
    st.markdown("**Storage**: SQLite (Synthetic Dataset)")
    st.markdown("**Graph Engine**: NetworkX + PyVis")

    st.markdown("---")
    st.markdown("### 🧪 Synthetic Benchmark Cases")
    st.markdown("""
    - **`TX1001`**: Money Mule & Shared Device Ring (`A102-A115`, `D77`, `M19`, `A500`)
    - **`TX2001`**: Layering & Circular Flow (`A201-A204`, `D105`, `M42`)
    - **`TX3001`**: Synthetic ID & Crypto Cashout (`A301-A303`, `D210`, `M60`)
    - **`TX9001`**: Legitimate Benign Baseline (`A901`, `D901`, `M05`)
    """)

    st.markdown("---")
    st.markdown("### 📊 Automated Test Evaluation")
    if st.button("▶️ Run Evaluation Benchmark", use_container_width=True):
        st.session_state["run_eval"] = True

    st.markdown("---")
    st.caption("🛡️ Autonomous Fraud Network Discovery • PS-3")

# Check if benchmark runner was triggered
if st.session_state.get("run_eval"):
    st.markdown("## 🧪 Automated Benchmark Evaluation Suite")
    st.caption("Evaluating Network Discovery Recall, Autonomous Tool Efficiency, and Risk Differentiation across planted networks.")

    benchmark_cases = [
        {"tx": "TX1001", "name": "Mule Fan-In Ring", "expected_accounts": {"A102", "A103", "A108", "A115"}, "expected_device": "D77", "min_score": 75},
        {"tx": "TX2001", "name": "Circular Layering Loop", "expected_accounts": {"A201", "A202", "A203", "A204"}, "expected_device": "D105", "min_score": 50},
        {"tx": "TX3001", "name": "Synthetic ID Cashout", "expected_accounts": {"A301", "A302", "A303"}, "expected_device": "D210", "min_score": 40},
        {"tx": "TX9001", "name": "Clean Legitimate Baseline", "expected_accounts": {"A901"}, "expected_device": "D901", "max_score": 15}
    ]

    results = []
    agent = FraudInvestigationAgent(provider="autonomous")

    for case in benchmark_cases:
        t0 = time.time()
        res_state = agent.investigate(case["tx"])
        t_el = round((time.time() - t0) * 1000, 1)

        found_accs = set(res_state.get_accounts())
        found_devs = set(res_state.get_devices())
        
        expected_accs = case["expected_accounts"]
        acc_recall = len(found_accs.intersection(expected_accs)) / len(expected_accs) * 100.0
        dev_recall = 100.0 if case["expected_device"] in found_devs else 0.0

        score = res_state.risk_evaluation.get("prototype_risk_score", 0)
        passed = (score >= case.get("min_score", 0)) and (score <= case.get("max_score", 100)) and (acc_recall >= 75)

        results.append({
            "Target Tx": case["tx"],
            "Network Topology": case["name"],
            "Accounts Recall": f"{acc_recall:.0f}% ({len(found_accs.intersection(expected_accs))}/{len(expected_accs)})",
            "Device Recall": f"{dev_recall:.0f}%",
            "Tool Calls": len(res_state.action_history),
            "Risk Score": f"{score}/100",
            "Execution Time": f"{t_el} ms",
            "Benchmark Status": "✅ PASS" if passed else "⚠️ REVIEW"
        })

    import pandas as pd
    st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)
    st.success("All benchmark test cases executed with empirical grounding from SQLite synthetic data.")
    if st.button("Close Benchmark Results"):
        st.session_state["run_eval"] = False
        st.rerun()

# Render primary dashboard
render_dashboard(st.session_state.get("state"), run_investigation)
