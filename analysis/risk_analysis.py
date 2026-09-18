"""Explainable risk evaluation and human investigator recommendation generator."""

from typing import Dict, Any, List

def compile_risk_evaluation(
    initial_tx: Dict[str, Any],
    discovered_nodes: List[Dict[str, Any]],
    discovered_edges: List[Dict[str, Any]],
    risk_summary: Dict[str, Any],
    topology_summary: Dict[str, Any]
) -> Dict[str, Any]:
    """Compile an explainable risk dossier synthesizing graph topology and empirical rules."""
    
    score = risk_summary.get("score", 0)
    severity = risk_summary.get("severity", "Low Risk / Clean")
    indicators = risk_summary.get("indicators", [])

    # Format human-readable evidence chain
    evidence_chain = []
    
    # 1. Starting transaction
    tx_id = initial_tx.get("transaction_id", "UNKNOWN")
    sender = initial_tx.get("sender_account", "UNKNOWN")
    amount = initial_tx.get("amount", 0.0)
    device = initial_tx.get("device_id")
    merchant = initial_tx.get("merchant_id")

    step_1 = f"Seed Transaction: {tx_id} originated from Account {sender} for ${amount:,.2f}."
    evidence_chain.append(step_1)

    if device:
        step_2 = f"Hardware Link: Transaction {tx_id} authenticated via Device {device}."
        evidence_chain.append(step_2)

    # 2. Shared device discovery
    shared_device_nodes = [n for n in discovered_nodes if n.get("type") == "Device"]
    account_nodes = [n for n in discovered_nodes if n.get("type") == "Account"]
    
    if shared_device_nodes and len(account_nodes) > 1:
        dev_ids = [d["id"] for d in shared_device_nodes]
        acc_ids = [a["id"] for a in account_nodes if a["id"] != sender]
        evidence_chain.append(
            f"Infrastructure Sharing: Device(s) {', '.join(dev_ids)} concurrently utilized by accounts: {', '.join(acc_ids)}."
        )

    # 3. Merchant linkage
    merchant_nodes = [n for n in discovered_nodes if n.get("type") == "Merchant"]
    if merchant_nodes:
        m_ids = [m["id"] for m in merchant_nodes]
        evidence_chain.append(
            f"Merchant Channel: Coordinated transactions routed through merchant entity: {', '.join(m_ids)}."
        )

    # 4. Beneficiary aggregator
    agg = topology_summary.get("aggregator_node")
    if agg:
        evidence_chain.append(
            f"Aggregator Funnel: Account {agg['node']} identified as primary convergence point with {agg['incoming_count']} inbound connections."
        )

    # 5. Circular loops
    cycles = topology_summary.get("circular_cycles", [])
    if cycles:
        cycle_str = " -> ".join(cycles[0])
        evidence_chain.append(
            f"Layering Loop: Circular fund round-tripping path verified: {cycle_str}."
        )

    return {
        "prototype_risk_score": score,
        "risk_severity": severity,
        "indicators": indicators,
        "evidence_chain": evidence_chain,
        "disclaimer": "This score is a prototype investigation metric based on synthetic graph indicators, intended exclusively to guide human investigator review. It does not constitute legal or regulatory proof of fraud."
    }

def generate_recommendations(
    risk_summary: Dict[str, Any],
    discovered_nodes: List[Dict[str, Any]],
    topology_summary: Dict[str, Any]
) -> List[Dict[str, str]]:
    """Generate prioritized next investigation steps for a human compliance officer."""
    recs = []

    score = risk_summary.get("score", 0)
    device_nodes = [n["id"] for n in discovered_nodes if n.get("type") == "Device"]
    account_nodes = [n["id"] for n in discovered_nodes if n.get("type") == "Account"]
    merchant_nodes = [n["id"] for n in discovered_nodes if n.get("type") == "Merchant"]
    cycles = topology_summary.get("circular_cycles", [])
    agg = topology_summary.get("aggregator_node")

    if score >= 75:
        recs.append({
            "priority": "P1 - Immediate Action",
            "action": "Escalate to Fraud Operations & AML Compliance Unit",
            "details": f"Submit coordinated network dossier encompassing {len(account_nodes)} accounts and shared infrastructure for enhanced due diligence (EDD) review."
        })
    
    if device_nodes:
        recs.append({
            "priority": "P2 - Device Forensics",
            "action": f"Audit hardware fingerprints for Device(s): {', '.join(device_nodes)}",
            "details": "Inspect session logs, proxy headers, emulator flags, and IP geo-velocity across all accounts associated with these hardware signatures."
        })

    if agg:
        recs.append({
            "priority": "P2 - Beneficiary Verification",
            "action": f"Investigate beneficiary account {agg['node']}",
            "details": f"Place temporary monitoring flag on incoming credits to {agg['node']}; verify ultimate beneficial ownership (UBO) and corporate registration."
        })

    if merchant_nodes:
        recs.append({
            "priority": "P3 - Merchant Review",
            "action": f"Review merchant processing logs for {', '.join(merchant_nodes)}",
            "details": "Examine settlement velocity, chargeback rates, and transaction fee agreements to identify potential collusive gateway behavior."
        })

    if cycles:
        recs.append({
            "priority": "P2 - AML Layering Probe",
            "action": "Trace round-trip fund routing (Layering)",
            "details": f"Investigate closed circular transaction loop ({' -> '.join(cycles[0])}) for potential trade-based money laundering or wash trading."
        })

    if score < 25:
        recs.append({
            "priority": "P4 - Routine Monitoring",
            "action": "Maintain Standard Account Monitoring",
            "details": "No coordinated network risk detected. Continue baseline automated anomaly monitoring for this account."
        })

    return recs
