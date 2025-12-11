#!/usr/bin/env python3
"""
Debug conversation balance issue
"""
import sqlite3
from pathlib import Path
import pandas as pd

db_path = Path.home() / "Library" / "Messages" / "chat.db"
conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, check_same_thread=False)

print("=== Investigating Conversation Balance ===\n")

# Sample query for a specific contact
query = """
SELECT 
    h.id as phone_number,
    COUNT(*) as total_messages,
    SUM(CASE WHEN m.is_from_me = 1 THEN 1 ELSE 0 END) as sent_by_me,
    SUM(CASE WHEN m.is_from_me = 0 THEN 1 ELSE 0 END) as received_from_them
FROM message m
LEFT JOIN handle h ON m.handle_id = h.ROWID
LEFT JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
LEFT JOIN chat c ON cmj.chat_id = c.ROWID
WHERE
    m.is_system_message = 0
    AND m.item_type = 0
    AND c.style != 43  -- Exclude group chats (style 43)
    AND h.id IS NOT NULL
GROUP BY h.id
ORDER BY total_messages DESC
LIMIT 10
"""

df = pd.read_sql_query(query, conn)
print("Top 10 contacts by message count:")
print(df.to_string())

print("\n=== Checking is_from_me distribution ===")
cursor = conn.execute("""
SELECT 
    is_from_me,
    COUNT(*) as count
FROM message
WHERE is_system_message = 0 AND item_type = 0
GROUP BY is_from_me
""")
for row in cursor.fetchall():
    print(f"is_from_me={row[0]}: {row[1]:,} messages")

print("\n=== Sample messages with is_from_me flag ===")
cursor = conn.execute("""
SELECT 
    m.ROWID,
    m.is_from_me,
    m.text,
    h.id as phone
FROM message m
LEFT JOIN handle h ON m.handle_id = h.ROWID
WHERE m.is_system_message = 0 AND m.item_type = 0
LIMIT 20
""")
for row in cursor.fetchall():
    text_preview = (row[2][:30] + '...') if row[2] else '[no text]'
    print(f"  ID: {row[0]}, from_me: {row[1]}, phone: {row[3]}, text: {text_preview}")

conn.close()
