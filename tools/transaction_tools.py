"""Transaction-level tools for autonomous investigation."""

from typing import Dict, Any, List, Optional
from .db import query_one, query_db

def get_transaction(transaction_id: str) -> Dict[str, Any]:
    """Retrieve detailed information about a specific transaction.
    
    Args:
        transaction_id: The unique identifier for the transaction (e.g. 'TX1001').
        
    Returns:
        Structured dictionary containing transaction attributes, sender, receiver,
        merchant, device, amount, timestamp, status, and transaction type.
    """
    if not transaction_id:
        return {"error": "Missing transaction_id"}

    sql = """
    SELECT 
        t.transaction_id,
        t.sender_account,
        t.receiver_account,
        t.merchant_id,
        t.amount,
        t.timestamp,
        t.transaction_type,
        t.status,
        t.device_id,
        s_cust.full_name as sender_name,
        r_cust.full_name as receiver_name,
        m.merchant_name,
        m.merchant_category,
        m.risk_tier as merchant_risk_tier,
        d.device_type,
        d.location as device_location,
        d.ip_address as device_ip
    FROM transactions t
    LEFT JOIN accounts s_acc ON t.sender_account = s_acc.account_id
    LEFT JOIN customers s_cust ON s_acc.customer_id = s_cust.customer_id
    LEFT JOIN accounts r_acc ON t.receiver_account = r_acc.account_id
    LEFT JOIN customers r_cust ON r_acc.customer_id = r_cust.customer_id
    LEFT JOIN merchants m ON t.merchant_id = m.merchant_id
    LEFT JOIN devices d ON t.device_id = d.device_id
    WHERE t.transaction_id = ?
    """
    res = query_one(sql, (transaction_id.strip(),))
    if not res:
        return {
            "found": False,
            "transaction_id": transaction_id,
            "message": f"Transaction {transaction_id} not found in database."
        }
    
    return {
        "found": True,
        "transaction_id": res["transaction_id"],
        "sender_account": res["sender_account"],
        "sender_name": res["sender_name"],
        "receiver_account": res["receiver_account"],
        "receiver_name": res["receiver_name"],
        "merchant_id": res["merchant_id"],
        "merchant_name": res["merchant_name"],
        "merchant_category": res["merchant_category"],
        "merchant_risk_tier": res["merchant_risk_tier"],
        "amount": res["amount"],
        "timestamp": res["timestamp"],
        "transaction_type": res["transaction_type"],
        "status": res["status"],
        "device_id": res["device_id"],
        "device_type": res["device_type"],
        "device_location": res["device_location"],
        "device_ip": res["device_ip"]
    }

def find_related_transactions(account_id: str, limit: int = 15) -> Dict[str, Any]:
    """Find transactions sent or received by a specific account.
    
    Args:
        account_id: The account identifier (e.g. 'A102').
        limit: Max transactions to return (default 15).
        
    Returns:
        Summary of inbound and outbound transactions, total volume, unique counterparties,
        and devices used.
    """
    if not account_id:
        return {"error": "Missing account_id"}
        
    sql = """
    SELECT 
        t.transaction_id,
        t.sender_account,
        t.receiver_account,
        t.merchant_id,
        t.amount,
        t.timestamp,
        t.transaction_type,
        t.status,
        t.device_id,
        m.merchant_name,
        d.device_type
    FROM transactions t
    LEFT JOIN merchants m ON t.merchant_id = m.merchant_id
    LEFT JOIN devices d ON t.device_id = d.device_id
    WHERE t.sender_account = ? OR t.receiver_account = ?
    ORDER BY t.timestamp DESC
    LIMIT ?
    """
    rows = query_db(sql, (account_id.strip(), account_id.strip(), limit))
    
    total_outbound = sum(r["amount"] for r in rows if r["sender_account"] == account_id)
    total_inbound = sum(r["amount"] for r in rows if r["receiver_account"] == account_id)
    unique_counterparties = list({
        r["receiver_account"] if r["sender_account"] == account_id else r["sender_account"]
        for r in rows if (r["receiver_account"] or r["sender_account"])
    } - {account_id, None})
    unique_devices = list({r["device_id"] for r in rows if r["device_id"]})
    unique_merchants = list({r["merchant_id"] for r in rows if r["merchant_id"]})

    return {
        "account_id": account_id,
        "transaction_count": len(rows),
        "total_outbound_volume": round(total_outbound, 2),
        "total_inbound_volume": round(total_inbound, 2),
        "counterparty_accounts": unique_counterparties,
        "devices_used": unique_devices,
        "merchants_used": unique_merchants,
        "transactions": rows
    }
