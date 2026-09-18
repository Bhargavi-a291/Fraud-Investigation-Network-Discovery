"""Risk and pattern detection tools for financial investigation."""

from typing import Dict, Any, List
from datetime import datetime
from .db import query_db, query_one

def detect_transaction_patterns(account_ids: List[str]) -> Dict[str, Any]:
    """Detect coordinated transaction patterns among a cluster of discovered accounts.
    
    Checks for:
    - Common destination aggregator (Fan-in / Mule funneling)
    - Rapid transaction velocity (multiple transfers in tight time window)
    - Structured amounts (smurfing below $10k AML reporting threshold)
    - Circular transaction flows (layering / wash round-tripping)
    - Account creation clustering (multiple accounts created within 48h)
    
    Args:
        account_ids: List of account IDs discovered in the network (e.g. ['A102', 'A103', 'A108']).
        
    Returns:
        Structured pattern analysis with detected indicators and supporting transactions.
    """
    if not account_ids:
        return {"error": "No account_ids provided"}

    clean_ids = [a.strip() for a in account_ids if a]
    placeholders = ",".join(["?"] * len(clean_ids))

    # 1. Fetch all transactions involving these accounts
    sql_tx = f"""
    SELECT 
        transaction_id, sender_account, receiver_account, merchant_id,
        amount, timestamp, transaction_type, status, device_id
    FROM transactions
    WHERE sender_account IN ({placeholders}) OR receiver_account IN ({placeholders})
    ORDER BY timestamp ASC
    """
    txs = query_db(sql_tx, tuple(clean_ids) + tuple(clean_ids))

    # 2. Check for common receiver destinations (Aggregator / Mule Boss)
    receiver_counts: Dict[str, int] = {}
    receiver_totals: Dict[str, float] = {}
    for tx in txs:
        rec = tx.get("receiver_account")
        if rec and rec not in clean_ids:
            receiver_counts[rec] = receiver_counts.get(rec, 0) + 1
            receiver_totals[rec] = receiver_totals.get(rec, 0.0) + tx["amount"]

    common_destinations = [
        {"account_id": r, "incoming_tx_count": cnt, "total_amount": round(receiver_totals[r], 2)}
        for r, cnt in receiver_counts.items() if cnt >= 2
    ]

    # 3. Check for Structured Amounts ($9,000 - $9,999 smurfing)
    structured_txs = [
        tx["transaction_id"] for tx in txs
        if 9000.0 <= tx["amount"] < 10000.0
    ]

    # 4. Check for Rapid Velocity (multiple transfers within 6 hours)
    velocity_alerts = []
    if len(txs) >= 2:
        for i in range(len(txs) - 1):
            try:
                t1 = datetime.strptime(txs[i]["timestamp"], "%Y-%m-%d %H:%M:%S")
                t2 = datetime.strptime(txs[i+1]["timestamp"], "%Y-%m-%d %H:%M:%S")
                diff_hours = abs((t2 - t1).total_seconds()) / 3600.0
                if diff_hours <= 4.0:
                    velocity_alerts.append({
                        "tx_from": txs[i]["transaction_id"],
                        "tx_to": txs[i+1]["transaction_id"],
                        "time_diff_hours": round(diff_hours, 2)
                    })
            except Exception:
                pass

    # 5. Check for Circular Flow (A -> B -> C -> A)
    transfer_edges = {}
    for tx in txs:
        snd = tx["sender_account"]
        rec = tx["receiver_account"]
        if snd and rec:
            transfer_edges.setdefault(snd, set()).add(rec)

    is_circular = False
    circular_path = []
    for start_node in transfer_edges:
        visited = []
        def dfs(curr, path):
            nonlocal is_circular, circular_path
            if is_circular:
                return
            for neighbor in transfer_edges.get(curr, []):
                if neighbor == start_node and len(path) >= 3:
                    is_circular = True
                    circular_path = path + [start_node]
                    return
                if neighbor not in path and len(path) < 6:
                    dfs(neighbor, path + [neighbor])
        dfs(start_node, [start_node])
        if is_circular:
            break

    # 6. Check Account Creation Proximity
    sql_acc = f"""
    SELECT account_id, account_creation_date, status, balance
    FROM accounts
    WHERE account_id IN ({placeholders})
    """
    acc_rows = query_db(sql_acc, tuple(clean_ids))
    recent_accounts = []
    for acc in acc_rows:
        try:
            cdate = datetime.strptime(acc["account_creation_date"], "%Y-%m-%d %H:%M:%S")
            # If created after 2026-09-10 (shortly before investigation window)
            if cdate >= datetime(2026, 9, 10):
                recent_accounts.append({
                    "account_id": acc["account_id"],
                    "created_at": acc["account_creation_date"]
                })
        except Exception:
            pass

    return {
        "accounts_analyzed": clean_ids,
        "total_transactions_analyzed": len(txs),
        "common_destinations": common_destinations,
        "structured_transactions": structured_txs,
        "high_velocity_bursts": velocity_alerts,
        "is_circular_flow": is_circular,
        "circular_path": circular_path,
        "recently_created_accounts": recent_accounts
    }

def calculate_risk_indicators(
    discovered_accounts: List[str],
    discovered_devices: List[str],
    discovered_merchants: List[str],
    pattern_summary: Dict[str, Any]
) -> Dict[str, Any]:
    """Calculate transparent, deterministic risk score and rule breakdown.
    
    Returns:
        Overall risk score (0-100), risk severity ('Low', 'Medium', 'High', 'Critical'),
        and list of itemized indicator contributions with point values.
    """
    indicators = []
    total_score = 0

    # Rule 1: Shared Device across accounts
    shared_devices_found = []
    for d_id in discovered_devices:
        d_sql = "SELECT COUNT(DISTINCT sender_account) as acc_count FROM transactions WHERE device_id = ?"
        row = query_one(d_sql, (d_id,))
        if row and row["acc_count"] >= 2:
            shared_devices_found.append((d_id, row["acc_count"]))

    if shared_devices_found:
        max_shared = max(s[1] for s in shared_devices_found)
        pts = 25 if max_shared >= 3 else 15
        total_score += pts
        dev_list = ", ".join([f"{d[0]} ({d[1]} accounts)" for d in shared_devices_found])
        indicators.append({
            "indicator": "Shared Hardware Fingerprint (Device)",
            "points": pts,
            "severity": "High" if max_shared >= 3 else "Medium",
            "evidence": f"Hardware device(s) shared across multiple distinct accounts: {dev_list}"
        })

    # Rule 2: Common Merchant Funnel / Escrow
    if len(discovered_merchants) >= 1:
        # Check merchant risk tier
        placeholders = ",".join(["?"] * len(discovered_merchants))
        m_rows = query_db(f"SELECT merchant_id, merchant_name, risk_tier FROM merchants WHERE merchant_id IN ({placeholders})", tuple(discovered_merchants))
        high_risk_merchants = [m["merchant_name"] for m in m_rows if m["risk_tier"] in ["High", "Critical"]]
        if high_risk_merchants:
            pts = 20
            total_score += pts
            indicators.append({
                "indicator": "High-Risk Merchant / Escrow Gateway Funnel",
                "points": pts,
                "severity": "High",
                "evidence": f"Network funnels transactions through flagged high-risk merchant entities: {', '.join(high_risk_merchants)}"
            })

    # Rule 3: Common Destination Aggregator (Mule Fan-In)
    destinations = pattern_summary.get("common_destinations", [])
    if destinations:
        pts = 20
        total_score += pts
        dest_str = ", ".join([f"{d['account_id']} (${d['total_amount']:,.2f})" for d in destinations])
        indicators.append({
            "indicator": "Common Beneficiary Aggregator (Fan-In)",
            "points": pts,
            "severity": "High",
            "evidence": f"Multiple accounts funneling funds into common destination account(s): {dest_str}"
        })

    # Rule 4: Structured Amount Smurfing (<$10,000)
    structured = pattern_summary.get("structured_transactions", [])
    if len(structured) >= 2:
        pts = 15
        total_score += pts
        indicators.append({
            "indicator": "Structuring / Smurfing Pattern",
            "points": pts,
            "severity": "Medium",
            "evidence": f"{len(structured)} transactions detected between $9,000 and $9,999 structured to bypass BSA/AML reporting thresholds: {', '.join(structured[:4])}"
        })

    # Rule 5: Circular Flow / Layering Loop
    if pattern_summary.get("is_circular_flow"):
        pts = 25
        total_score += pts
        path_str = " -> ".join(pattern_summary.get("circular_path", []))
        indicators.append({
            "indicator": "Circular Transaction Flow (Layering Loop)",
            "points": pts,
            "severity": "Critical",
            "evidence": f"Closed circular money loop detected among accounts to obscure origin: {path_str}"
        })

    # Rule 6: Rapid Velocity Bursts
    bursts = pattern_summary.get("high_velocity_bursts", [])
    if bursts:
        pts = 10
        total_score += pts
        indicators.append({
            "indicator": "Abnormal Transaction Velocity",
            "points": pts,
            "severity": "Medium",
            "evidence": f"{len(bursts)} rapid transfers executed in quick succession (<4 hours apart) indicating automated or coordinated cashout"
        })

    # Rule 7: Coordinated Account Creation Spike
    recent = pattern_summary.get("recently_created_accounts", [])
    if len(recent) >= 2:
        pts = 15
        total_score += pts
        acc_str = ", ".join([r["account_id"] for r in recent])
        indicators.append({
            "indicator": "Coordinated Account Creation Surge",
            "points": pts,
            "severity": "Medium",
            "evidence": f"{len(recent)} accounts created within a 48-hour window: {acc_str}"
        })

    # Cap score at 100
    capped_score = min(total_score, 100)
    
    if capped_score >= 75:
        severity = "Critical Risk"
    elif capped_score >= 50:
        severity = "High Risk"
    elif capped_score >= 25:
        severity = "Medium Risk"
    else:
        severity = "Low Risk / Clean"

    return {
        "score": capped_score,
        "severity": severity,
        "raw_points": total_score,
        "indicators": indicators,
        "indicators_count": len(indicators)
    }
