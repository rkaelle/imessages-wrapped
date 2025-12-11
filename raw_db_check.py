#!/usr/bin/env python3
"""
Raw database investigation - what's really in there?
"""
import sqlite3
from pathlib import Path

db_path = Path.home() / "Library" / "Messages" / "chat.db"
conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
conn.row_factory = sqlite3.Row

print("=== RAW DATABASE INVESTIGATION ===\n")

# Total messages
cursor = conn.execute("SELECT COUNT(*) FROM message")
print(f"Total messages in database: {cursor.fetchone()[0]:,}")

# Messages with text
cursor = conn.execute("SELECT COUNT(*) FROM message WHERE text IS NOT NULL AND text != ''")
print(f"Messages with text: {cursor.fetchone()[0]:,}")

# Messages with NULL text
cursor = conn.execute("SELECT COUNT(*) FROM message WHERE text IS NULL")
print(f"Messages with NULL text: {cursor.fetchone()[0]:,}")

# Messages with empty string text
cursor = conn.execute("SELECT COUNT(*) FROM message WHERE text = ''")
print(f"Messages with empty string text: {cursor.fetchone()[0]:,}")

# Check our query filters
cursor = conn.execute("""
SELECT COUNT(*) FROM message 
WHERE is_system_message = 0 AND item_type = 0
""")
print(f"\nMessages after our filters (not system, item_type=0): {cursor.fetchone()[0]:,}")

cursor = conn.execute("""
SELECT COUNT(*) FROM message 
WHERE is_system_message = 0 AND item_type = 0 AND text IS NOT NULL AND text != ''
""")
print(f"With text after filters: {cursor.fetchone()[0]:,}")

# Check item_type distribution
print("\n=== Item Type Distribution ===")
cursor = conn.execute("""
SELECT item_type, COUNT(*) as count
FROM message
GROUP BY item_type
ORDER BY count DESC
""")
for row in cursor.fetchall():
    print(f"  item_type={row['item_type']}: {row['count']:,}")

# Check is_system_message
print("\n=== System Message Check ===")
cursor = conn.execute("""
SELECT is_system_message, COUNT(*) as count
FROM message
GROUP BY is_system_message
""")
for row in cursor.fetchall():
    print(f"  is_system_message={row['is_system_message']}: {row['count']:,}")

# Sample messages WITH text
print("\n=== Sample Messages WITH Text (first 10) ===")
cursor = conn.execute("""
SELECT ROWID, text, is_from_me, item_type
FROM message
WHERE text IS NOT NULL AND text != '' AND LENGTH(text) > 10
LIMIT 10
""")
for row in cursor.fetchall():
    text_preview = row['text'][:60] if row['text'] else '[None]'
    print(f"  ID {row['ROWID']}: from_me={row['is_from_me']}, type={row['item_type']}, text='{text_preview}...'")

# Sample messages WITHOUT text (are they attachments?)
print("\n=== Sample Messages WITHOUT Text ===")
cursor = conn.execute("""
SELECT m.ROWID, m.text, m.is_from_me, m.item_type, m.cache_has_attachments,
       (SELECT COUNT(*) FROM message_attachment_join WHERE message_id = m.ROWID) as attachment_count
FROM message m
WHERE m.text IS NULL OR m.text = ''
LIMIT 10
""")
for row in cursor.fetchall():
    print(f"  ID {row['ROWID']}: from_me={row['is_from_me']}, type={row['item_type']}, attachments={row['attachment_count']}, has_attach={row['cache_has_attachments']}")

conn.close()
