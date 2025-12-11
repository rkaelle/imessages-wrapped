#!/usr/bin/env python3
"""
Debug conversation balance and group chat issues
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.database import iMessageDatabase
from src.analyzer import MessageAnalyzer
import pandas as pd

print("=== Testing Conversation Balance ===\n")

# Load messages
with iMessageDatabase() as db:
    messages_df = db.get_messages()

print(f"Total messages loaded: {len(messages_df):,}")
print(f"Columns: {messages_df.columns.tolist()}")

# Check is_group distribution
print(f"\nis_group distribution:")
print(messages_df['is_group'].value_counts())

# Check is_from_me distribution
print(f"\nis_from_me distribution:")
print(messages_df['is_from_me'].value_counts())

# Test analyzer
analyzer = MessageAnalyzer(messages_df)

# Get conversation balance
balance = analyzer.get_conversation_balance(5)
print(f"\nConversation Balance (top 5):")
print(balance)

# Sample a specific contact
if len(balance) > 0:
    first_contact = balance.iloc[0]
    print(f"\nFirst contact details:")
    print(f"  Name: {first_contact['display_name']}")
    print(f"  Sent: {first_contact['messages_sent']} (type: {type(first_contact['messages_sent'])})")
    print(f"  Received: {first_contact['messages_received']} (type: {type(first_contact['messages_received'])})")
    print(f"  Balance: {first_contact['balance_pct']}%")

# Check group chats
print(f"\n=== Testing Group Chats ===\n")
groups = analyzer.get_group_chat_stats(5)
print(f"Group chats found: {len(groups)}")
if len(groups) > 0:
    print(groups[['chat_name', 'total_messages', 'participants', 'your_participation_pct']])
