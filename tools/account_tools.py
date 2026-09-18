"""Account and Customer Identity investigation tools."""

from typing import Dict, Any, List
from .db import query_one, query_db

def get_account_profile(account_id: str) -> Dict[str, Any]:
    """Retrieve full profile of an account including holder identity and associated devices.
    
    Args:
        account_id: Unique account identifier (e.g. 'A102').
        
    Returns:
        Dictionary containing account creation date, type, status, customer identity,
        KYC verification status, and all devices associated with account activity.
    """
    if not account_id:
        return {"error": "Missing account_id"}
        
    sql = """
    SELECT 
        a.account_id,
        a.customer_id,
        a.account_creation_date,
        a.account_type,
        a.status as account_status,
        a.balance,
        c.full_name,
        c.email,
        c.phone,
        c.identity_id,
        c.country,
        c.verification_status,
        c.created_at as customer_created_at
    FROM accounts a
    JOIN customers c ON a.customer_id = c.customer_id
    WHERE a.account_id = ?
    """
    acc = query_one(sql, (account_id.strip(),))
    if not acc:
        return {"found": False, "account_id": account_id, "message": f"Account {account_id} not found."}

    # Find devices used by this account in transactions
    dev_sql = """
    SELECT DISTINCT 
        d.device_id,
        d.device_type,
        d.ip_address,
        d.location,
        COUNT(t.transaction_id) as usage_count
    FROM transactions t
    JOIN devices d ON t.device_id = d.device_id
    WHERE t.sender_account = ?
    GROUP BY d.device_id
    """
    devices = query_db(dev_sql, (account_id.strip(),))

    # Find primary merchants interacted with
    merch_sql = """
    SELECT DISTINCT 
        m.merchant_id,
        m.merchant_name,
        m.merchant_category,
        m.risk_tier,
        COUNT(t.transaction_id) as tx_count,
        SUM(t.amount) as total_spent
    FROM transactions t
    JOIN merchants m ON t.merchant_id = m.merchant_id
    WHERE t.sender_account = ?
    GROUP BY m.merchant_id
    """
    merchants = query_db(merch_sql, (account_id.strip(),))

    return {
        "found": True,
        "account_id": acc["account_id"],
        "customer_id": acc["customer_id"],
        "customer_name": acc["full_name"],
        "identity_id": acc["identity_id"],
        "phone": acc["phone"],
        "email": acc["email"],
        "country": acc["country"],
        "verification_status": acc["verification_status"],
        "account_creation_date": acc["account_creation_date"],
        "account_type": acc["account_type"],
        "account_status": acc["account_status"],
        "balance": acc["balance"],
        "associated_devices": devices,
        "associated_merchants": merchants
    }

def get_identity_profile(customer_id: str) -> Dict[str, Any]:
    """Retrieve full KYC and identity profile of a customer, plus any co-linked accounts or identities.
    
    Args:
        customer_id: Unique customer ID (e.g. 'C102').
        
    Returns:
        Customer details, KYC status, all owned accounts, and potential duplicate/shared identities.
    """
    if not customer_id:
        return {"error": "Missing customer_id"}

    sql = """
    SELECT 
        customer_id, full_name, email, phone, identity_id,
        country, verification_status, created_at
    FROM customers
    WHERE customer_id = ?
    """
    cust = query_one(sql, (customer_id.strip(),))
    if not cust:
        return {"found": False, "customer_id": customer_id, "message": f"Customer {customer_id} not found."}

    # Accounts owned by this customer
    acc_sql = "SELECT account_id, account_type, account_creation_date, status, balance FROM accounts WHERE customer_id = ?"
    accounts = query_db(acc_sql, (customer_id.strip(),))

    # Shared identity or phone check (synthetic identity indicator)
    colink_sql = """
    SELECT customer_id, full_name, email, phone, identity_id, verification_status
    FROM customers
    WHERE (identity_id = ? OR phone = ?) AND customer_id != ?
    """
    co_linked = query_db(colink_sql, (cust["identity_id"], cust["phone"], customer_id.strip()))

    return {
        "found": True,
        "customer_id": cust["customer_id"],
        "full_name": cust["full_name"],
        "identity_id": cust["identity_id"],
        "phone": cust["phone"],
        "email": cust["email"],
        "country": cust["country"],
        "verification_status": cust["verification_status"],
        "created_at": cust["created_at"],
        "owned_accounts": accounts,
        "co_linked_identities": co_linked
    }
