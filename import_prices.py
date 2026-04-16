#!/usr/bin/env python3
"""
Aquatech Price Importer
=======================
Reads prices.xlsx and uploads custom per-customer pricing to Firebase Firestore.
Run this script any time you update prices.xlsx in the repo.

Excel format (prices.xlsx)
--------------------------
Column A  email    — customer email  (e.g. john@example.com)
Column B  code     — product code    (e.g. PT18)
Column C  price    — price per box   (e.g. 12.50)

Example rows:
  email                  code    price
  john@plumbing.com      PT18    12.50
  john@plumbing.com      GF4      8.75
  sarah@supply.com       PT18    11.00
  sarah@supply.com       BV12C    5.25

Requirements
------------
    pip install pandas openpyxl firebase-admin

Setup
-----
1. Go to Firebase Console → Project Settings → Service Accounts
2. Click "Generate new private key" → save as serviceAccountKey.json
3. Place serviceAccountKey.json in this same folder
4. Run:  python import_prices.py

Firestore structure written
---------------------------
  prices/{customer_email}  →  { "PT18": 12.50, "GF4": 8.75, ... }
"""

import sys
import os
import json
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore

# Accept the Excel path as an optional command-line argument.
# Usage examples:
#   python import_prices.py                                      <- looks for prices.xlsx next to this script
#   python import_prices.py "C:\Users\rsond\Desktop\prices.xlsx" <- full path anywhere on your machine
if len(sys.argv) > 1:
    EXCEL_FILE = sys.argv[1]
else:
    # Fall back: check script folder, then Desktop
    _script_dir  = os.path.dirname(os.path.abspath(__file__))
    _desktop     = os.path.join(os.path.expanduser('~'), 'Desktop', 'prices.xlsx')
    _local       = os.path.join(_script_dir, 'prices.xlsx')
    EXCEL_FILE   = _local if os.path.exists(_local) else _desktop

SERVICE_ACCOUNT = 'serviceAccountKey.json'
COLLECTION      = 'prices'


def main():
    # -- Init Firebase --
    # GitHub Actions supplies the key as an env var; local runs use the file.
    _sa_env = os.environ.get('FIREBASE_SERVICE_ACCOUNT')
    if _sa_env:
        cred = credentials.Certificate(json.loads(_sa_env))
    else:
        try:
            cred = credentials.Certificate(SERVICE_ACCOUNT)
        except FileNotFoundError:
            print(f"ERROR: {SERVICE_ACCOUNT} not found.")
            print("Download it from Firebase Console → Project Settings → Service Accounts.")
            sys.exit(1)
    firebase_admin.initialize_app(cred)

    db = firestore.client()

    # -- Read Excel --
    try:
        df = pd.read_excel(EXCEL_FILE)
    except FileNotFoundError:
        print(f"ERROR: {EXCEL_FILE} not found.")
        sys.exit(1)

    # Normalize column names (strip whitespace, lowercase)
    df.columns = [str(c).strip().lower() for c in df.columns]

    required = {'email', 'code', 'price'}
    missing  = required - set(df.columns)
    if missing:
        print(f"ERROR: Excel is missing columns: {missing}")
        print(f"Found columns: {list(df.columns)}")
        sys.exit(1)

    # Drop rows with missing values
    df = df.dropna(subset=['email', 'code', 'price'])
    df['email'] = df['email'].astype(str).str.strip().str.lower()
    df['code']  = df['code'].astype(str).str.strip()
    df['price'] = pd.to_numeric(df['price'], errors='coerce')
    df = df.dropna(subset=['price'])

    # -- Upload to Firestore (one document per customer) --
    count_customers = 0
    count_prices    = 0

    for email, group in df.groupby('email'):
        prices = {row['code']: round(float(row['price']), 2) for _, row in group.iterrows()}
        db.collection(COLLECTION).document(email).set(prices)
        print(f"  {email}  →  {len(prices)} price(s) uploaded")
        count_customers += 1
        count_prices    += len(prices)

    print(f"\nDone — {count_prices} prices uploaded for {count_customers} customer(s).")


if __name__ == '__main__':
    main()
