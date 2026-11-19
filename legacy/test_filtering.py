#!/usr/bin/env python3
"""
Quick test of is_from_me filtering
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.database import iMessageDatabase

with iMessageDatabase() as db:
    messages_df = db.get_messages()

# Filter to one contact's messages
test_phone = "+19252573470"
contact_msgs = messages_df[messages_df['phone_number'] == test_phone]

print(f"Messages for {test_phone}: {len(contact_msgs)}")
print(f"\nis_from_me unique values: {contact_msgs['is_from_me'].unique()}")
print(f"is_from_me dtype: {contact_msgs['is_from_me'].dtype}")

# Test filtering
sent = contact_msgs[contact_msgs['is_from_me'] == 1]
received = contact_msgs[contact_msgs['is_from_me'] == 0]

print(f"\nDirect filtering:")
print(f"  Sent (== 1): {len(sent)}")
print(f"  Received (== 0): {len(received)}")

# Test sum method
sent_sum = (contact_msgs['is_from_me'] == 1).sum()
received_sum = (contact_msgs['is_from_me'] == 0).sum()

print(f"\nSum method:")
print(f"  Sent sum: {sent_sum}")
print(f"  Received sum: {received_sum}")

# Check sample messages
print(f"\nSample messages:")
print(contact_msgs[['is_from_me', 'text']].head(10))
