#!/usr/bin/env python3
"""
Deep dive into sent/received messages
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.database import iMessageDatabase

with iMessageDatabase() as db:
    messages_df = db.get_messages()

# Check specific contact
test_phone = "+19252573470"

print(f"=== Analyzing {test_phone} ===\n")

# All messages for this contact
all_msgs = messages_df[messages_df['phone_number'] == test_phone]
print(f"Total messages: {len(all_msgs)}")

# Check is_group
group_msgs = all_msgs[all_msgs['is_group'] == True]
one_on_one_msgs = all_msgs[all_msgs['is_group'] == False]
print(f"Group messages: {len(group_msgs)}")
print(f"1-on-1 messages: {len(one_on_one_msgs)}")

# Check sent/received in 1-on-1
if len(one_on_one_msgs) > 0:
    sent = one_on_one_msgs[one_on_one_msgs['is_from_me'] == 1]
    received = one_on_one_msgs[one_on_one_msgs['is_from_me'] == 0]
    print(f"\n1-on-1 breakdown:")
    print(f"  Sent: {len(sent)}")
    print(f"  Received: {len(received)}")
    
    print(f"\nis_from_me values in 1-on-1: {one_on_one_msgs['is_from_me'].unique()}")
    print(f"is_from_me value counts:")
    print(one_on_one_msgs['is_from_me'].value_counts())

# Sample messages
print(f"\nSample 1-on-1 messages:")
print(one_on_one_msgs[['is_from_me', 'is_group', 'chat_style', 'text']].head(20))
