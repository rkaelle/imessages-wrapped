#!/usr/bin/env python3
"""
Debug word counting
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.database import iMessageDatabase

with iMessageDatabase() as db:
    messages_df = db.get_messages()

print(f"Total messages: {len(messages_df):,}")

# Check text column
text_msgs = messages_df[messages_df['text'].notna() & (messages_df['text'] != '')]
print(f"Messages with text: {len(text_msgs):,}")

# Check text content
non_empty = messages_df[messages_df['text'].str.len() > 0]
print(f"Messages with non-empty text: {len(non_empty):,}")

# Sample some text
print("\nSample texts:")
for i, row in text_msgs.head(10).iterrows():
    text_preview = row['text'][:50] if row['text'] else '[None]'
    print(f"  {text_preview}...")

# Check longest texts
longest = text_msgs.nlargest(5, 'text').apply(lambda x: len(x['text']) if x['text'] else 0)
print(f"\nLongest message lengths:")
for i, row in text_msgs.nlargest(5, 'text').iterrows():
    print(f"  {len(row['text'])} chars: {row['text'][:80]}...")

# Count all words
all_words = []
for text in text_msgs['text'].dropna():
    if text:
        all_words.extend(text.lower().split())

print(f"\nTotal words found: {len(all_words):,}")
print(f"Unique words: {len(set(all_words)):,}")
