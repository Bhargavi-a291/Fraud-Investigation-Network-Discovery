"""Synthetic Financial Data Generator with Planted Coordinated Fraud Networks.

Generates:
- accounts
- customers
- devices
- merchants
- transactions

Planted Networks:
1. Network 1 (Seed TX1001): Mule ring (A102, A103, A108, A115) sharing Device D77 and Merchant M19, funneling to A500.
2. Network 2 (Seed TX2001): Circular layering ring (A201 -> A202 -> A203 -> A204 -> A201) sharing Device D105.
3. Network 3 (Seed TX3001): Synthetic identity cluster (C301, C302, C303) sharing Device D210, unverified KYC, rapid cashout via M60.
4. Benign Baseline (Seed TX9001): Legitimate grocery purchase from verified customer A901 on dedicated Device D901.
"""

import os
import sqlite3
import random
from datetime import datetime, timedelta

def get_db_path():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "fraud.db")

def create_schema(cursor):
    cursor.execute("DROP TABLE IF EXISTS transactions;")
    cursor.execute("DROP TABLE IF EXISTS accounts;")
    cursor.execute("DROP TABLE IF EXISTS customers;")
    cursor.execute("DROP TABLE IF EXISTS devices;")
    cursor.execute("DROP TABLE IF EXISTS merchants;")

    cursor.execute("""
    CREATE TABLE customers (
        customer_id TEXT PRIMARY KEY,
        full_name TEXT NOT NULL,
        email TEXT NOT NULL,
        phone TEXT NOT NULL,
        identity_id TEXT NOT NULL,
        country TEXT NOT NULL,
        verification_status TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE accounts (
        account_id TEXT PRIMARY KEY,
        customer_id TEXT NOT NULL,
        account_creation_date TEXT NOT NULL,
        account_type TEXT NOT NULL,
        status TEXT NOT NULL,
        balance REAL NOT NULL,
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
    );
    """)

    cursor.execute("""
    CREATE TABLE devices (
        device_id TEXT PRIMARY KEY,
        device_type TEXT NOT NULL,
        ip_address TEXT NOT NULL,
        location TEXT NOT NULL,
        first_seen TEXT NOT NULL,
        last_seen TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE merchants (
        merchant_id TEXT PRIMARY KEY,
        merchant_name TEXT NOT NULL,
        merchant_category TEXT NOT NULL,
        risk_tier TEXT NOT NULL,
        location TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE transactions (
        transaction_id TEXT PRIMARY KEY,
        sender_account TEXT NOT NULL,
        receiver_account TEXT,
        merchant_id TEXT,
        amount REAL NOT NULL,
        timestamp TEXT NOT NULL,
        transaction_type TEXT NOT NULL,
        status TEXT NOT NULL,
        device_id TEXT,
        FOREIGN KEY (sender_account) REFERENCES accounts(account_id),
        FOREIGN KEY (receiver_account) REFERENCES accounts(account_id),
        FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id),
        FOREIGN KEY (device_id) REFERENCES devices(device_id)
    );
    """)

    # Performance indices
    cursor.execute("CREATE INDEX idx_tx_sender ON transactions(sender_account);")
    cursor.execute("CREATE INDEX idx_tx_receiver ON transactions(receiver_account);")
    cursor.execute("CREATE INDEX idx_tx_merchant ON transactions(merchant_id);")
    cursor.execute("CREATE INDEX idx_tx_device ON transactions(device_id);")
    cursor.execute("CREATE INDEX idx_acc_customer ON accounts(customer_id);")

def generate_synthetic_database(db_path=None):
    if db_path is None:
        db_path = get_db_path()

    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    create_schema(cursor)

    random.seed(42)

    # Base reference date for transactions (approx recent)
    base_time = datetime(2026, 9, 15, 10, 0, 0)

    # 1. GENERATE MERCHANTS
    merchants_data = [
        ("M19", "Apex Escrow & Logistics", "Escrow / Wire Service", "High", "Panama City, PA"),
        ("M42", "Nexus Global Forex", "Digital Currency Exchange", "High", "Nicosia, CY"),
        ("M60", "CryptoVault Cashout", "Crypto / Cashout Service", "Critical", "St. George, AG"),
        ("M05", "Metro Grocers", "Supermarket", "Low", "New York, US"),
        ("M06", "QuickFuel Express", "Gas Station", "Low", "Chicago, US"),
        ("M07", "Urban Brew Cafe", "Food & Beverage", "Low", "Austin, US"),
        ("M08", "TechHub Electronics", "Consumer Electronics", "Medium", "San Francisco, US"),
        ("M09", "CloudHost Digital", "Cloud Services", "Low", "Seattle, US"),
        ("M10", "Prime Logistics Fleet", "Shipping", "Medium", "Miami, US")
    ]
    existing_m_ids = {m[0] for m in merchants_data}
    for i in range(11, 45):
        m_id = f"M{i:02d}"
        if m_id in existing_m_ids:
            continue
        name = f"Merchant Retailer {i}"
        cat = random.choice(["Retail", "Dining", "Travel", "Software", "Healthcare"])
        tier = random.choice(["Low", "Low", "Low", "Medium"])
        loc = random.choice(["New York, US", "London, UK", "Toronto, CA", "Dallas, US", "Denver, US"])
        merchants_data.append((m_id, name, cat, tier, loc))

    cursor.executemany(
        "INSERT INTO merchants VALUES (?, ?, ?, ?, ?)",
        merchants_data
    )

    # 2. GENERATE DEVICES
    devices_data = [
        ("D77", "Android 14 Emulator", "198.51.100.77", "Eastern Europe / Proxy", "2026-09-10 08:00:00", "2026-09-15 14:00:00"),
        ("D105", "Linux Tor Gateway", "203.0.113.105", "Zurich, CH / VPN", "2026-09-12 11:30:00", "2026-09-15 15:30:00"),
        ("D210", "Windows VM Spoofer", "192.0.2.210", "Nairobi, KE / Hosting", "2026-09-14 02:00:00", "2026-09-15 16:00:00"),
        ("D901", "Apple iPhone 15 Pro", "72.14.201.99", "Boston, US", "2023-01-15 09:00:00", "2026-09-15 09:12:00")
    ]
    for i in range(1, 65):
        d_id = f"D{i:03d}"
        if d_id in ["D077", "D105", "D210", "D901"]:
            continue
        dtype = random.choice(["iPhone 14", "Samsung S23", "MacBook Pro", "Windows 11 PC", "Pixel 8"])
        ip = f"{random.randint(24, 210)}.{random.randint(10, 250)}.{random.randint(1, 250)}.{random.randint(1, 250)}"
        loc = random.choice(["New York, US", "Los Angeles, US", "Chicago, US", "London, UK", "Sydney, AU"])
        first = (base_time - timedelta(days=random.randint(60, 500))).strftime("%Y-%m-%d %H:%M:%S")
        last = (base_time - timedelta(hours=random.randint(1, 48))).strftime("%Y-%m-%d %H:%M:%S")
        devices_data.append((d_id, dtype, ip, loc, first, last))

    cursor.executemany(
        "INSERT INTO devices VALUES (?, ?, ?, ?, ?, ?)",
        devices_data
    )

    # 3. GENERATE CUSTOMERS
    customers_data = [
        # Network 1: Mule Ring identities (often disposable or synthetic)
        ("C102", "Alex Mercer", "alex.m.102@tempmail.org", "+1-555-0102", "ID-US-99102", "United States", "Unverified", "2026-09-13 09:00:00"),
        ("C103", "Arthur Vance", "avance.biz@guerrillamail.com", "+1-555-0103", "ID-US-99103", "United States", "Unverified", "2026-09-13 09:45:00"),
        ("C108", "David Sterling", "d.sterling88@mailinator.com", "+1-555-0108", "ID-US-99108", "United States", "Unverified", "2026-09-13 14:10:00"),
        ("C115", "Elena Rostova", "elena.r115@proton.me", "+1-555-0115", "ID-CY-99115", "Cyprus", "Unverified", "2026-09-13 15:30:00"),
        ("C500", "Titan Aggregator Holdings", "treasury@titan-capital.offshore", "+44-20-7946-0500", "ID-BVI-50001", "British Virgin Islands", "Suspicious/Flagged", "2025-11-01 10:00:00"),

        # Network 2: Circular Layering ring
        ("C201", "Klaus Richter", "k.richter@layer-node.eu", "+49-30-1234-201", "ID-DE-88201", "Germany", "Verified", "2026-08-01 10:00:00"),
        ("C202", "Marco Bellini", "m.bellini@layer-node.eu", "+39-06-698-202", "ID-IT-88202", "Italy", "Verified", "2026-08-02 11:00:00"),
        ("C203", "Jean-Pierre Laurent", "jp.laurent@layer-node.eu", "+33-1-4268-203", "ID-FR-88203", "France", "Verified", "2026-08-03 12:00:00"),
        ("C204", "Viktor Novak", "v.novak@layer-node.eu", "+420-2-2189-204", "ID-CZ-88204", "Czech Republic", "Verified", "2026-08-04 14:00:00"),

        # Network 3: Synthetic Identity Cluster
        ("C301", "Michael A. Thorne", "mthorne@shadowidentity.cc", "+1-555-0301", "SYN-998811", "United States", "Unverified", "2026-09-14 01:10:00"),
        ("C302", "Michelle A. Thorne", "mthorne2@shadowidentity.cc", "+1-555-0301", "SYN-998811", "United States", "Unverified", "2026-09-14 01:25:00"),
        ("C303", "M. Anthony Thorne", "mthorne3@shadowidentity.cc", "+1-555-0301", "SYN-998811", "United States", "Unverified", "2026-09-14 01:40:00"),

        # Benign Baseline
        ("C901", "Sarah Jenkins", "sarah.jenkins@gmail.com", "+1-617-555-0901", "ID-US-44901", "United States", "Verified", "2023-01-10 10:00:00")
    ]

    first_names = ["James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda", "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica", "Thomas", "Sarah", "Charles", "Karen"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin"]

    for i in range(1, 140):
        cid = f"C{i+500}"
        fn = f"{random.choice(first_names)} {random.choice(last_names)}"
        email = f"{fn.lower().replace(' ', '.')}@example.com"
        phone = f"+1-555-{random.randint(1000, 9999)}"
        id_num = f"ID-US-{random.randint(10000, 99999)}"
        cntry = "United States"
        status = "Verified" if random.random() > 0.1 else "Pending"
        cdate = (base_time - timedelta(days=random.randint(90, 800))).strftime("%Y-%m-%d %H:%M:%S")
        customers_data.append((cid, fn, email, phone, id_num, cntry, status, cdate))

    cursor.executemany(
        "INSERT INTO customers VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        customers_data
    )

    # 4. GENERATE ACCOUNTS
    accounts_data = [
        # Network 1: Mule Accounts (rapidly created 2 days before TX1001)
        ("A102", "C102", "2026-09-13 10:15:00", "Personal Checking", "Active", 1240.00),
        ("A103", "C103", "2026-09-13 11:20:00", "Personal Checking", "Active", 890.00),
        ("A108", "C108", "2026-09-13 14:30:00", "Personal Checking", "Active", 1150.00),
        ("A115", "C115", "2026-09-13 16:00:00", "Business Checking", "Active", 450.00),
        ("A500", "C500", "2025-11-02 09:00:00", "Corporate Settlement", "Active", 384000.00),

        # Network 2: Circular Layering Accounts
        ("A201", "C201", "2026-08-01 12:00:00", "Investment Account", "Active", 25000.00),
        ("A202", "C202", "2026-08-02 12:00:00", "Investment Account", "Active", 18500.00),
        ("A203", "C203", "2026-08-03 12:00:00", "Investment Account", "Active", 22000.00),
        ("A204", "C204", "2026-08-04 12:00:00", "Investment Account", "Active", 19200.00),

        # Network 3: Synthetic Identity Accounts
        ("A301", "C301", "2026-09-14 02:00:00", "Digital Wallet", "Active", 500.00),
        ("A302", "C302", "2026-09-14 02:15:00", "Digital Wallet", "Active", 320.00),
        ("A303", "C303", "2026-09-14 02:30:00", "Digital Wallet", "Active", 210.00),

        # Benign Baseline
        ("A901", "C901", "2023-01-11 14:00:00", "Personal Checking", "Active", 8450.00)
    ]

    # Generate background accounts
    for i in range(1, 140):
        acc_id = f"A{i+600}"
        cust_id = f"C{i+500}"
        adate = (base_time - timedelta(days=random.randint(100, 750))).strftime("%Y-%m-%d %H:%M:%S")
        atype = random.choice(["Personal Checking", "Savings", "Business Checking", "Credit Card"])
        astatus = "Active"
        abal = round(random.uniform(500.0, 45000.0), 2)
        accounts_data.append((acc_id, cust_id, adate, atype, astatus, abal))

    cursor.executemany(
        "INSERT INTO accounts VALUES (?, ?, ?, ?, ?, ?)",
        accounts_data
    )

    # 5. GENERATE TRANSACTIONS
    transactions_data = []

    # =========================================================================
    # PLANTED NETWORK 1: Fan-in Mule Ring around TX1001
    # Seed TX1001: A102 sends $9,850 via M19 with Device D77
    # =========================================================================
    transactions_data.append((
        "TX1001", "A102", "A500", "M19", 9850.00,
        "2026-09-15 08:30:00", "Merchant Wire", "Completed", "D77"
    ))
    transactions_data.append((
        "TX1002", "A103", "A500", "M19", 9920.00,
        "2026-09-15 08:45:00", "Merchant Wire", "Completed", "D77"
    ))
    transactions_data.append((
        "TX1003", "A108", "A500", "M19", 9750.00,
        "2026-09-15 09:15:00", "Merchant Wire", "Completed", "D77"
    ))
    transactions_data.append((
        "TX1004", "A115", "A500", "M19", 9800.00,
        "2026-09-15 09:40:00", "Merchant Wire", "Completed", "D77"
    ))
    # Inter-mule prep transfers
    transactions_data.append((
        "TX1005", "A102", "A103", None, 3500.00,
        "2026-09-14 20:10:00", "P2P Transfer", "Completed", "D77"
    ))
    transactions_data.append((
        "TX1006", "A108", "A115", None, 4200.00,
        "2026-09-14 21:05:00", "P2P Transfer", "Completed", "D77"
    ))
    # Direct funnel from A103 to A500
    transactions_data.append((
        "TX1007", "A103", "A500", None, 8500.00,
        "2026-09-15 11:00:00", "ACH Transfer", "Completed", "D77"
    ))

    # =========================================================================
    # PLANTED NETWORK 2: Circular Wash Trading Layering Ring around TX2001
    # Seed TX2001: A201 -> A202 ($14,500)
    # Loop: A201 -> A202 -> A203 -> A204 -> A201 using Device D105 & M42
    # =========================================================================
    transactions_data.append((
        "TX2001", "A201", "A202", "M42", 14500.00,
        "2026-09-15 12:00:00", "Forex Arbitrage", "Completed", "D105"
    ))
    transactions_data.append((
        "TX2002", "A202", "A203", "M42", 14450.00,
        "2026-09-15 12:15:00", "Forex Arbitrage", "Completed", "D105"
    ))
    transactions_data.append((
        "TX2003", "A203", "A204", "M42", 14400.00,
        "2026-09-15 12:30:00", "Forex Arbitrage", "Completed", "D105"
    ))
    transactions_data.append((
        "TX2004", "A204", "A201", "M42", 14350.00,
        "2026-09-15 12:45:00", "Forex Arbitrage", "Completed", "D105"
    ))
    transactions_data.append((
        "TX2005", "A201", "A203", None, 7200.00,
        "2026-09-15 13:10:00", "Direct Wire", "Completed", "D105"
    ))

    # =========================================================================
    # PLANTED NETWORK 3: Synthetic Identity & Rapid Cashout Cluster around TX3001
    # Seed TX3001: A301 -> M60 ($8,200)
    # Device D210 shared by A301, A302, A303
    # =========================================================================
    transactions_data.append((
        "TX3001", "A301", None, "M60", 8200.00,
        "2026-09-15 03:00:00", "Crypto Buy", "Completed", "D210"
    ))
    transactions_data.append((
        "TX3002", "A302", None, "M60", 7900.00,
        "2026-09-15 03:20:00", "Crypto Buy", "Completed", "D210"
    ))
    transactions_data.append((
        "TX3003", "A303", None, "M60", 8100.00,
        "2026-09-15 03:45:00", "Crypto Buy", "Completed", "D210"
    ))
    transactions_data.append((
        "TX3004", "A301", "A302", None, 2500.00,
        "2026-09-14 23:00:00", "Instant Transfer", "Completed", "D210"
    ))

    # =========================================================================
    # BENIGN BASELINE: Legitimate Consumer Purchase TX9001
    # =========================================================================
    transactions_data.append((
        "TX9001", "A901", None, "M05", 45.20,
        "2026-09-15 09:12:00", "POS Debit", "Completed", "D901"
    ))
    transactions_data.append((
        "TX9002", "A901", None, "M06", 32.50,
        "2026-09-12 17:30:00", "POS Debit", "Completed", "D901"
    ))
    transactions_data.append((
        "TX9003", "A901", None, "M07", 8.75,
        "2026-09-14 08:15:00", "POS Debit", "Completed", "D901"
    ))
    transactions_data.append((
        "TX9004", "A901", "A610", None, 120.00,
        "2026-09-01 19:00:00", "P2P Reimbursement", "Completed", "D901"
    ))

    # =========================================================================
    # BACKGROUND BENIGN TRANSACTIONS (600+ transactions)
    # Random normal activity among accounts A601..A739
    # =========================================================================
    bg_accounts = [f"A{i+600}" for i in range(1, 139)]
    bg_merchants = [f"M{i:02d}" for i in range(5, 45)]
    bg_devices = [f"D{i:03d}" for i in range(1, 65) if f"D{i:03d}" not in ["D077", "D105", "D210", "D901"]]

    tx_counter = 4000
    for acc in bg_accounts:
        # 4 to 8 normal transactions per account over past 30 days
        num_tx = random.randint(4, 8)
        acc_device = random.choice(bg_devices)
        for _ in range(num_tx):
            tx_counter += 1
            tx_id = f"TX{tx_counter}"
            t_delta = timedelta(days=random.randint(1, 25), hours=random.randint(0, 23), minutes=random.randint(0, 59))
            t_time = (base_time - t_delta).strftime("%Y-%m-%d %H:%M:%S")

            if random.random() < 0.7:
                # Merchant purchase
                m_id = random.choice(bg_merchants)
                amt = round(random.uniform(5.50, 280.00), 2)
                ttype = random.choice(["POS Debit", "Online Purchase", "Card Payment"])
                transactions_data.append((tx_id, acc, None, m_id, amt, t_time, ttype, "Completed", acc_device))
            else:
                # P2P or bill pay
                rec_acc = random.choice(bg_accounts)
                if rec_acc == acc:
                    rec_acc = f"A{((int(acc[1:]) + 3) % 138) + 601}"
                amt = round(random.uniform(15.00, 750.00), 2)
                ttype = random.choice(["P2P Transfer", "Bill Payment", "Bank Wire"])
                transactions_data.append((tx_id, acc, rec_acc, None, amt, t_time, ttype, "Completed", acc_device))

    cursor.executemany(
        "INSERT INTO transactions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        transactions_data
    )

    conn.commit()
    conn.close()
    print(f"Successfully generated synthetic fraud database at: {db_path}")
    print(f"Total Customers: {len(customers_data)}")
    print(f"Total Accounts: {len(accounts_data)}")
    print(f"Total Devices: {len(devices_data)}")
    print(f"Total Merchants: {len(merchants_data)}")
    print(f"Total Transactions: {len(transactions_data)}")

if __name__ == "__main__":
    generate_synthetic_database()
