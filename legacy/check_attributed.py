#!/usr/bin/env python3
"""
Check all columns in message table
"""
import sqlite3
from pathlib import Path

db_path = Path.home() / "Library" / "Messages" / "chat.db"
conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)

# Get column info
print("=== MESSAGE TABLE COLUMNS ===\n")
cursor = conn.execute("PRAGMA table_info(message)")
columns = cursor.fetchall()
for col in columns:
    print(f"  {col[1]} ({col[2]})")

# Check attributedBody column
print("\n=== Checking attributedBody ===")
cursor = conn.execute("SELECT COUNT(*) FROM message WHERE attributedBody IS NOT NULL")
print(f"Messages with attributedBody: {cursor.fetchone()[0]:,}")

# Sample attributedBody
print("\n=== Sample attributedBody (trying to decode) ===")
cursor = conn.execute("""
SELECT ROWID, text, attributedBody 
FROM message 
WHERE attributedBody IS NOT NULL
LIMIT 5
""")
for row in cursor.fetchall():
    body = row[2]
    if body:
        # Try to decode - attributedBody is typically NSKeyedArchiver data
        try:
            # Look for readable text in the blob
            decoded = body.decode('utf-8', errors='ignore')
            # Find readable portions
            readable = ''.join(c if c.isprintable() else ' ' for c in decoded)
            readable = ' '.join(readable.split())[:100]
            print(f"  ID {row[0]}: text='{row[1]}' | decoded body='{readable}...'")
        except:
            print(f"  ID {row[0]}: text='{row[1]}' | (binary blob)")

# Check if newer messages have attributedBody
print("\n=== Recent messages with attributedBody ===")
cursor = conn.execute("""
SELECT ROWID, text, LENGTH(attributedBody) as body_len, is_from_me
FROM message 
WHERE attributedBody IS NOT NULL
ORDER BY ROWID DESC
LIMIT 10
""")
for row in cursor.fetchall():
    print(f"  ID {row[0]}: text='{row[1]}', body_len={row[2]}, from_me={row[3]}")

conn.close()
