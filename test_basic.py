#!/usr/bin/env python3
"""
Basic test script for iMessage Wrapped
Tests core functionality without requiring all dependencies
"""

import sys
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

def test_database_connection():
    """Test database connection"""
    print("Testing database connection...")
    db_path = Path.home() / "Library" / "Messages" / "chat.db"

    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cursor = conn.execute("SELECT COUNT(*) FROM message WHERE is_system_message = 0")
        count = cursor.fetchone()[0]
        print(f"✓ Database connected: {count:,} messages found")
        conn.close()
        return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False

def test_imports():
    """Test if all modules can be imported"""
    print("\nTesting module imports...")

    try:
        from src.database import iMessageDatabase
        print("✓ database.py imports successfully")
    except Exception as e:
        print(f"✗ database.py import failed: {e}")
        return False

    try:
        from src.utils import get_time_period, format_number
        print("✓ utils.py imports successfully")
    except Exception as e:
        print(f"✗ utils.py import failed: {e}")
        return False

    # Test analyzer and visualizations (might fail if dependencies missing)
    try:
        from src.analyzer import MessageAnalyzer
        print("✓ analyzer.py imports successfully")
    except Exception as e:
        print(f"⚠ analyzer.py import failed (might need pandas): {e}")

    try:
        from src.visualizations import VisualizationGenerator
        print("✓ visualizations.py imports successfully")
    except Exception as e:
        print(f"⚠ visualizations.py import failed (might need matplotlib): {e}")

    return True

def test_database_class():
    """Test iMessageDatabase class"""
    print("\nTesting iMessageDatabase class...")

    try:
        from src.database import iMessageDatabase

        db = iMessageDatabase()
        stats = db.get_stats()

        print(f"✓ Total messages: {stats['total_messages']:,}")
        print(f"✓ Total conversations: {stats['total_conversations']:,}")
        print(f"✓ Total contacts: {stats['total_contacts']:,}")
        print(f"✓ Date range: {stats['first_message']} to {stats['last_message']}")

        db.close()
        return True
    except Exception as e:
        print(f"✗ iMessageDatabase test failed: {e}")
        return False

def test_utils():
    """Test utility functions"""
    print("\nTesting utility functions...")

    try:
        from src.utils import format_number, format_duration, get_time_period

        assert format_number(1500) == "1.5K"
        assert format_number(2500000) == "2.5M"
        print("✓ format_number() works")

        assert format_duration(5) == "5m"
        assert format_duration(90) == "1h 30m"
        print("✓ format_duration() works")

        start, end = get_time_period("past_year")
        assert (end - start).days >= 365
        print("✓ get_time_period() works")

        return True
    except Exception as e:
        print(f"✗ Utils test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("iMessage Wrapped - Basic Tests")
    print("=" * 60)

    results = []

    results.append(("Database Connection", test_database_connection()))
    results.append(("Module Imports", test_imports()))
    results.append(("Database Class", test_database_class()))
    results.append(("Utility Functions", test_utils()))

    print("\n" + "=" * 60)
    print("Test Results:")
    print("=" * 60)

    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:10} {name}")

    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)

    print("=" * 60)
    print(f"Passed: {passed_count}/{total_count}")

    if passed_count == total_count:
        print("\n✓ All tests passed! Basic functionality is working.")
        print("\nTo install full dependencies and run the app:")
        print("  python3 -m pip install --user -r requirements.txt")
        print("  streamlit run web/app.py")
    else:
        print("\n⚠ Some tests failed. Check errors above.")

if __name__ == "__main__":
    main()
