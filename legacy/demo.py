#!/usr/bin/env python3
"""
Quick demo to show what iMessage Wrapped will do
Requires dependencies installed: run setup.sh first
"""

import sys
from pathlib import Path

def main():
    print("=" * 70)
    print("iMessage Wrapped - Demo")
    print("=" * 70)
    print()

    try:
        # Import modules
        from src.database import iMessageDatabase
        from src.analyzer import MessageAnalyzer
        from src.visualizations import VisualizationGenerator
        from src.utils import get_time_period, format_number

        # Connect to database
        print("📱 Connecting to iMessage database...")
        db = iMessageDatabase()

        # Get stats
        print("📊 Loading database statistics...")
        stats = db.get_stats()

        print()
        print("Database Statistics:")
        print("-" * 70)
        print(f"  Total Messages:     {format_number(stats['total_messages'])}")
        print(f"  Total Conversations: {format_number(stats['total_conversations'])}")
        print(f"  Total Contacts:      {format_number(stats['total_contacts'])}")
        print(f"  First Message:       {stats['first_message']}")
        print(f"  Last Message:        {stats['last_message']}")
        print()

        # Load messages for past year
        print("📅 Loading messages from past year...")
        start_date, end_date = get_time_period("past_year")
        messages = db.get_messages(start_date, end_date)

        print(f"✓ Loaded {len(messages):,} messages from past year")
        print()

        # Run analysis
        print("🔍 Running analytics...")
        analyzer = MessageAnalyzer(messages)

        # Summary
        summary = analyzer.get_summary_stats()
        print()
        print("Past Year Summary:")
        print("-" * 70)
        print(f"  Total Messages:      {format_number(summary['total_messages'])}")
        print(f"  Messages Sent:       {format_number(summary['messages_sent'])}")
        print(f"  Messages Received:   {format_number(summary['messages_received'])}")
        print(f"  Conversations:       {summary['conversations']}")
        print(f"  Contacts:            {summary['contacts']}")
        print(f"  Group Chats:         {summary['group_chats']}")
        print()

        # Top contacts
        print("👥 Top 5 Contacts:")
        print("-" * 70)
        top_contacts = analyzer.get_top_contacts(5)
        for idx, row in top_contacts.iterrows():
            print(f"  {idx + 1}. {row['display_name']:20} - {format_number(row['total_messages'])} messages")
        print()

        # Time personality
        print("⏰ Your Messaging Personality:")
        print("-" * 70)
        personality = analyzer.get_messaging_personality()
        print(f"  Time:        {personality['time_personality']}")
        print(f"  Style:       {personality['length_personality']}")
        print(f"  Emojis:      {personality['emoji_personality']}")
        print(f"  Social:      {personality['initiation_personality']}")
        print()

        # Emoji stats
        emoji_stats = analyzer.get_emoji_stats(5)
        if emoji_stats['total_emojis'] > 0:
            print("😊 Top Emojis:")
            print("-" * 70)
            for emoji, count in emoji_stats['top_emojis']:
                print(f"  {emoji}  {count:,} times")
            print()

        # Generate visualizations
        print("🎨 Generating shareable images...")
        viz = VisualizationGenerator()
        viz.generate_all_images(analyzer, "Past Year", anonymize=False)

        print()
        print("=" * 70)
        print("✓ Demo Complete!")
        print("=" * 70)
        print()
        print(f"📁 Images saved to: {Path('output').absolute()}")
        print()
        print("To see the full interactive dashboard:")
        print("  streamlit run web/app.py")
        print()

        db.close()

    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        print()
        print("Please run the setup script first:")
        print("  ./setup.sh")
        print()
        print("Or manually:")
        print("  python3 -m venv venv")
        print("  source venv/bin/activate")
        print("  pip install -r requirements.txt")
        sys.exit(1)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
