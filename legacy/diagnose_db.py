#!/usr/bin/env python3
"""
Diagnostic script to check iMessage database contents
"""
import sqlite3
from pathlib import Path

db_path = Path.home() / "Library" / "Messages" / "chat.db"

print(f"Checking database at: {db_path}")
print(f"Database exists: {db_path.exists()}\n")

if not db_path.exists():
    print("ERROR: Database file not found!")
    exit(1)

conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, check_same_thread=False)

# Total messages (all types)
cursor = conn.execute("SELECT COUNT(*) as count FROM message")
total_all = cursor.fetchone()[0]
print(f"Total messages (all types): {total_all:,}")

# Non-system messages
cursor = conn.execute("SELECT COUNT(*) as count FROM message WHERE is_system_message = 0")
total_non_system = cursor.fetchone()[0]
print(f"Non-system messages: {total_non_system:,}")

# Messages with text
cursor = conn.execute("SELECT COUNT(*) as count FROM message WHERE text IS NOT NULL")
total_with_text = cursor.fetchone()[0]
print(f"Messages with text: {total_with_text:,}")

# Non-system messages with text
cursor = conn.execute("SELECT COUNT(*) as count FROM message WHERE is_system_message = 0 AND text IS NOT NULL")
non_system_with_text = cursor.fetchone()[0]
print(f"Non-system messages with text: {non_system_with_text:,}")

# Non-system messages with text and item_type = 0
cursor = conn.execute("SELECT COUNT(*) as count FROM message WHERE is_system_message = 0 AND text IS NOT NULL AND item_type = 0")
filtered = cursor.fetchone()[0]
print(f"Non-system, text, item_type=0: {filtered:,}")

print("\n--- Current Query Filters (UPDATED - no text filter) ---")
# This is what the app NOW queries after fix
query = """
SELECT COUNT(*) as count
FROM message m
LEFT JOIN handle h ON m.handle_id = h.ROWID
LEFT JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
LEFT JOIN chat c ON cmj.chat_id = c.ROWID
WHERE
    m.is_system_message = 0
    AND m.item_type = 0
"""
cursor = conn.execute(query)
current_query_count = cursor.fetchone()[0]
print(f"Updated app query returns: {current_query_count:,}")

print("\n--- Without LEFT JOINs ---")
# Try without the joins to see if that's the issue
simple_query = """
SELECT COUNT(*) as count
FROM message m
WHERE
    m.is_system_message = 0
    AND m.item_type = 0
    AND m.text IS NOT NULL
"""
cursor = conn.execute(simple_query)
simple_count = cursor.fetchone()[0]
print(f"Simple query (no joins): {simple_count:,}")

print("\n--- Checking sample messages ---")
cursor = conn.execute("""
SELECT 
    m.ROWID,
    m.text,
    m.is_from_me,
    m.handle_id,
    m.date,
    cmj.chat_id
FROM message m
LEFT JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
WHERE m.is_system_message = 0 AND m.item_type = 0 AND m.text IS NOT NULL
LIMIT 5
""")
print("First 5 messages:")
for row in cursor.fetchall():
    print(f"  ID: {row[0]}, From me: {row[2]}, Has chat_id: {row[5] is not None}, Text: {row[1][:50]}...")

conn.close()
print("\nDiagnostic complete!")
