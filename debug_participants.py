#!/usr/bin/env python3
"""
Debug group chat participants and top contacts ratio
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.database import iMessageDatabase
from src.analyzer import MessageAnalyzer
import sqlite3

print("=== Testing Group Chat Participants ===\n")

# Direct database query
db_path = Path.home() / "Library" / "Messages" / "chat.db"
conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, check_same_thread=False)

# Check chat_handle_join table for participant counts
print("Sample group chat participants:")
cursor = conn.execute("""
SELECT 
    c.ROWID as chat_id,
    c.display_name,
    COUNT(DISTINCT chj.handle_id) as participant_count
FROM chat c
LEFT JOIN chat_handle_join chj ON c.ROWID = chj.chat_id
WHERE c.style = 43  -- Group chats
GROUP BY c.ROWID
HAVING participant_count > 0
ORDER BY participant_count DESC
LIMIT 5
""")
for row in cursor.fetchall():
    print(f"  Chat {row[0]}: {row[2]} participants, name='{row[1]}'")

conn.close()

print("\n=== Testing Top Contacts ===\n")

# Load messages
with iMessageDatabase() as db:
    messages_df = db.get_messages()

analyzer = MessageAnalyzer(messages_df)
contacts = analyzer.get_top_contacts(5)

print("Top 5 contacts:")
print(contacts[['display_name', 'total_messages', 'messages_sent', 'messages_received']])
print("\nColumn types:")
print(contacts.dtypes)
