"""Network discovery tools for unearthing multi-entity links and shared infrastructure."""

from typing import Dict, Any, List
from .db import query_one, query_db

def get_device_connections(device_id: str) -> Dict[str, Any]:
    """Retrieve all accounts, customers, and transactions linked to a specific physical/virtual device.
    
    Args:
        device_id: Device identifier (e.g. 'D77').
        
    Returns:
        Device metadata, list of distinct accounts and customers operating from this device,
        and transaction count summary. Crucial for detecting device-sharing mule rings.
    """
    if not device_id:
        return {"error": "Missing device_id"}

    sql_dev = "SELECT * FROM devices WHERE device_id = ?"
    device = query_one(sql_dev, (device_id.strip(),))
    if not device:
        return {"found": False, "device_id": device_id, "message": f"Device {device_id} not found."}

    sql_accounts = """
    SELECT 
        a.account_id,
        a.customer_id,
        c.full_name,
        a.account_creation_date,
        a.status as account_status,
        COUNT(t.transaction_id) as tx_count,
        SUM(t.amount) as total_volume,
        MIN(t.timestamp) as first_tx,
        MAX(t.timestamp) as last_tx
    FROM transactions t
    JOIN accounts a ON t.sender_account = a.account_id
    JOIN customers c ON a.customer_id = c.customer_id
    WHERE t.device_id = ?
    GROUP BY a.account_id
    ORDER BY tx_count DESC
    """
    connected_accounts = query_db(sql_accounts, (device_id.strip(),))

    return {
        "found": True,
        "device_id": device["device_id"],
        "device_type": device["device_type"],
        "ip_address": device["ip_address"],
        "location": device["location"],
        "first_seen": device["first_seen"],
        "last_seen": device["last_seen"],
        "unique_accounts_count": len(connected_accounts),
        "connected_accounts": connected_accounts,
        "is_shared_device": len(connected_accounts) > 1
    }

def get_merchant_connections(merchant_id: str) -> Dict[str, Any]:
    """Retrieve all accounts and transaction activity funneling through a specific merchant.
    
    Args:
        merchant_id: Merchant identifier (e.g. 'M19').
        
    Returns:
        Merchant category, risk tier, location, interacting accounts, volume, and recent transactions.
    """
    if not merchant_id:
        return {"error": "Missing merchant_id"}

    sql_m = "SELECT * FROM merchants WHERE merchant_id = ?"
    merchant = query_one(sql_m, (merchant_id.strip(),))
    if not merchant:
        return {"found": False, "merchant_id": merchant_id, "message": f"Merchant {merchant_id} not found."}

    sql_accs = """
    SELECT 
        a.account_id,
        c.full_name,
        COUNT(t.transaction_id) as tx_count,
        SUM(t.amount) as total_amount,
        MAX(t.timestamp) as last_interaction
    FROM transactions t
    JOIN accounts a ON t.sender_account = a.account_id
    JOIN customers c ON a.customer_id = c.customer_id
    WHERE t.merchant_id = ?
    GROUP BY a.account_id
    ORDER BY total_amount DESC
    """
    interacting_accounts = query_db(sql_accs, (merchant_id.strip(),))

    return {
        "found": True,
        "merchant_id": merchant["merchant_id"],
        "merchant_name": merchant["merchant_name"],
        "merchant_category": merchant["merchant_category"],
        "risk_tier": merchant["risk_tier"],
        "location": merchant["location"],
        "unique_accounts_count": len(interacting_accounts),
        "interacting_accounts": interacting_accounts
    }

def find_connected_accounts(entity_type: str, entity_id: str) -> Dict[str, Any]:
    """Find all accounts linked to an entity by relationship type.
    
    Args:
        entity_type: Type of entity ('device', 'merchant', 'customer', 'account').
        entity_id: The entity identifier.
        
    Returns:
        Discovered connected accounts with relationship labels.
    """
    etype = entity_type.lower().strip()
    eid = entity_id.strip()

    if etype == "device":
        res = get_device_connections(eid)
        if not res.get("found"):
            return res
        return {
            "entity_type": "device",
            "entity_id": eid,
            "relationship": "USES_DEVICE",
            "connected_accounts": [acc["account_id"] for acc in res.get("connected_accounts", [])]
        }
    elif etype == "merchant":
        res = get_merchant_connections(eid)
        if not res.get("found"):
            return res
        return {
            "entity_type": "merchant",
            "entity_id": eid,
            "relationship": "INTERACTS_WITH_MERCHANT",
            "connected_accounts": [acc["account_id"] for acc in res.get("interacting_accounts", [])]
        }
    elif etype in ["customer", "identity"]:
        sql = "SELECT account_id FROM accounts WHERE customer_id = ?"
        rows = query_db(sql, (eid,))
        return {
            "entity_type": "customer",
            "entity_id": eid,
            "relationship": "OWNS_ACCOUNT",
            "connected_accounts": [r["account_id"] for r in rows]
        }
    elif etype == "account":
        sql = """
        SELECT DISTINCT receiver_account as connected_acc FROM transactions WHERE sender_account = ? AND receiver_account IS NOT NULL
        UNION
        SELECT DISTINCT sender_account as connected_acc FROM transactions WHERE receiver_account = ?
        """
        rows = query_db(sql, (eid, eid))
        return {
            "entity_type": "account",
            "entity_id": eid,
            "relationship": "TRANSACTS_WITH",
            "connected_accounts": [r["connected_acc"] for r in rows if r["connected_acc"] and r["connected_acc"] != eid]
        }
    else:
        return {"error": f"Unsupported entity type: {entity_type}"}
