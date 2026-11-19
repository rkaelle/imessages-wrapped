#!/usr/bin/env python3
"""
Diagnostic script to check contact name sources
"""
import sqlite3
from pathlib import Path

db_path = Path.home() / "Library" / "Messages" / "chat.db"
conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, check_same_thread=False)

print("=== Contact Information Sources ===\n")

# Check handle table
print("Sample handles:")
cursor = conn.execute("""
SELECT ROWID, id, service, uncanonicalized_id
FROM handle 
WHERE id IS NOT NULL
LIMIT 10
""")
for row in cursor.fetchall():
    print(f"  ID: {row[0]}, Handle: {row[1]}, Service: {row[2]}")

# Check if there's a contact/address book integration
cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
print(f"\nAvailable tables: {', '.join(sorted(tables))}")

# Check chat table for display names
print("\n=== Chat Display Names ===")
cursor = conn.execute("""
SELECT ROWID, display_name, chat_identifier, style
FROM chat
WHERE display_name IS NOT NULL
LIMIT 10
""")
print("Chats with display names:")
for row in cursor.fetchall():
    print(f"  Chat ID: {row[0]}, Name: '{row[1]}', Identifier: {row[2]}, Style: {row[3]}")

# Count chats with/without names
cursor = conn.execute("SELECT COUNT(*) FROM chat WHERE display_name IS NOT NULL")
with_names = cursor.fetchone()[0]
cursor = conn.execute("SELECT COUNT(*) FROM chat WHERE display_name IS NULL")
without_names = cursor.fetchone()[0]
print(f"\nChats with names: {with_names}, without names: {without_names}")

# Check if there's an ABPerson or contact table
if 'ABPerson' in tables:
    print("\n=== ABPerson table found ===")
    cursor = conn.execute("SELECT * FROM ABPerson LIMIT 5")
    print(f"Columns: {[desc[0] for desc in cursor.description]}")

# Check message types
print("\n=== Message Type Distribution ===")
cursor = conn.execute("""
SELECT 
    CASE 
        WHEN text IS NOT NULL THEN 'text'
        ELSE 'non-text'
    END as type,
    COUNT(*) as count
FROM message
WHERE is_system_message = 0 AND item_type = 0
GROUP BY type
""")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]:,}")

# Check attachment info
if 'attachment' in tables:
    print("\n=== Attachment Information ===")
    cursor = conn.execute("SELECT COUNT(*) FROM attachment")
    attachment_count = cursor.fetchone()[0]
    print(f"Total attachments: {attachment_count:,}")
    
    cursor = conn.execute("""
    SELECT mime_type, COUNT(*) as count
    FROM attachment
    WHERE mime_type IS NOT NULL
    GROUP BY mime_type
    ORDER BY count DESC
    LIMIT 10
    """)
    print("\nTop attachment types:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]:,}")

conn.close()
