"""
iMessage Database Access Layer
Provides safe, read-only access to the iMessage SQLite database
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple


class iMessageDatabase:
    """Interface to the local iMessage SQLite database"""

    # macOS Cocoa epoch (2001-01-01) in nanoseconds
    COCOA_EPOCH = datetime(2001, 1, 1)

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database connection

        Args:
            db_path: Optional path to chat.db. Defaults to ~/Library/Messages/chat.db
        """
        if db_path is None:
            db_path = Path.home() / "Library" / "Messages" / "chat.db"

        self.db_path = Path(db_path)
        self.conn = None
        self._connect()

    def _connect(self):
        """Establish database connection in read-only mode"""
        try:
            # Open database in read-only mode to prevent any modifications
            # Use check_same_thread=False for Streamlit compatibility (read-only is safe)
            self.conn = sqlite3.connect(
                f"file:{self.db_path}?mode=ro",
                uri=True,
                check_same_thread=False
            )
            self.conn.row_factory = sqlite3.Row
        except sqlite3.Error as e:
            raise Exception(f"Failed to connect to iMessage database: {e}")

    @staticmethod
    def decode_attributed_body(blob: bytes) -> Optional[str]:
        """
        Decode attributedBody BLOB to extract text content
        
        Args:
            blob: The attributedBody BLOB data
            
        Returns:
            Extracted text string or None if decoding fails
        """
        if not blob:
            return None
        
        try:
            # The attributedBody is an NSKeyedArchiver plist
            # The text is embedded as NSString data
            # Try to decode and extract readable text
            decoded = blob.decode('utf-8', errors='ignore')
            
            # Look for text after 'NSString' marker
            # The format is: ...NSString...+<length><actual_text>...
            # Find readable portions
            text_parts = []
            i = 0
            while i < len(decoded):
                # Look for printable sequences
                if decoded[i].isprintable() and decoded[i] not in '\x00\x01\x02\x03\x04\x05':
                    start = i
                    while i < len(decoded) and decoded[i].isprintable():
                        i += 1
                    part = decoded[start:i].strip()
                    # Filter out metadata strings
                    if (len(part) > 2 and 
                        not part.startswith('NS') and 
                        not part.startswith('__kIM') and
                        not 'streamtyped' in part and
                        not 'Attribute' in part and
                        not 'Dictionary' in part):
                        text_parts.append(part)
                else:
                    i += 1
            
            if text_parts:
                # Return the longest meaningful text
                result = max(text_parts, key=len)
                if len(result) > 1:
                    return result.strip()
            
            return None
        except Exception:
            return None

    @staticmethod
    def convert_timestamp(apple_timestamp: int) -> datetime:
        """
        Convert Apple Core Data timestamp to Python datetime

        Args:
            apple_timestamp: Nanoseconds since 2001-01-01

        Returns:
            datetime object
        """
        if not apple_timestamp or apple_timestamp <= 0:
            return None

        # Convert nanoseconds to seconds
        seconds = apple_timestamp / 1_000_000_000
        return iMessageDatabase.COCOA_EPOCH + timedelta(seconds=seconds)

    def get_messages(self, start_date: Optional[datetime] = None,
                     end_date: Optional[datetime] = None) -> pd.DataFrame:
        """
        Retrieve all messages within date range

        Args:
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)

        Returns:
            DataFrame with columns: message_id, text, date, is_from_me, handle_id,
                                   phone_number, is_group, chat_id, chat_name
        """
        query = """
        SELECT
            m.ROWID as message_id,
            m.text,
            m.attributedBody,
            m.date,
            m.date_read,
            m.date_delivered,
            m.is_from_me,
            m.handle_id,
            m.cache_roomnames,
            m.is_read,
            h.id as phone_number,
            c.ROWID as chat_id,
            c.display_name as chat_name,
            c.style as chat_style
        FROM message m
        LEFT JOIN handle h ON m.handle_id = h.ROWID
        LEFT JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
        LEFT JOIN chat c ON cmj.chat_id = c.ROWID
        WHERE
            m.is_system_message = 0
            AND m.item_type = 0
        """

        params = []
        if start_date:
            # Convert to Apple timestamp
            delta = start_date - self.COCOA_EPOCH
            apple_ts = int(delta.total_seconds() * 1_000_000_000)
            query += " AND m.date >= ?"
            params.append(apple_ts)

        if end_date:
            delta = end_date - self.COCOA_EPOCH
            apple_ts = int(delta.total_seconds() * 1_000_000_000)
            query += " AND m.date <= ?"
            params.append(apple_ts)

        query += " ORDER BY m.date ASC"
        # Execute query
        df = pd.read_sql_query(query, self.conn, params=params)

        # Convert timestamp to datetime
        df['date'] = df['date'].apply(self.convert_timestamp)
        df['date_read'] = df['date_read'].apply(lambda x: self.convert_timestamp(x) if pd.notna(x) else None)
        df['date_delivered'] = df['date_delivered'].apply(lambda x: self.convert_timestamp(x) if pd.notna(x) else None)

        # Decode attributedBody to get text when text column is NULL
        def get_text(row):
            if row['text'] and str(row['text']).strip():
                return row['text']
            elif row['attributedBody'] is not None:
                decoded = self.decode_attributed_body(row['attributedBody'])
                return decoded if decoded else ''
            return ''
        
        df['text'] = df.apply(get_text, axis=1)
        
        # Drop the attributedBody column as we don't need it anymore
        df = df.drop('attributedBody', axis=1)

        # Determine if message is part of a group chat
        # Style 43 = named group chat
        # Style 45 = iMessage group
        # Any chat_style indicating group messaging
        df['is_group'] = df['chat_style'].apply(lambda x: x == 43 if pd.notna(x) else False)

        return df

    def get_contacts(self) -> pd.DataFrame:
        """
        Get all unique contacts

        Returns:
            DataFrame with contact information
        """
        query = """
        SELECT DISTINCT
            h.ROWID as handle_id,
            h.id as phone_number,
            h.service
        FROM handle h
        WHERE h.id IS NOT NULL
        """

        return pd.read_sql_query(query, self.conn)

    def get_group_chats(self) -> pd.DataFrame:
        """
        Get all group chats with participant counts

        Returns:
            DataFrame with group chat information
        """
        query = """
        SELECT
            c.ROWID as chat_id,
            c.display_name as chat_name,
            c.chat_identifier,
            COUNT(DISTINCT chj.handle_id) as participant_count,
            COUNT(DISTINCT cmj.message_id) as message_count
        FROM chat c
        LEFT JOIN chat_handle_join chj ON c.ROWID = chj.chat_id
        LEFT JOIN chat_message_join cmj ON c.ROWID = cmj.chat_id
        WHERE c.style = 45  -- Group chats
        GROUP BY c.ROWID
        HAVING message_count > 0
        ORDER BY message_count DESC
        """

        return pd.read_sql_query(query, self.conn)

    def get_conversation_participants(self, chat_id: int) -> list:
        """
        Get all participants in a conversation

        Args:
            chat_id: The chat ROWID

        Returns:
            List of phone numbers/emails
        """
        query = """
        SELECT h.id as phone_number
        FROM chat_handle_join chj
        JOIN handle h ON chj.handle_id = h.ROWID
        WHERE chj.chat_id = ?
        """

        cursor = self.conn.execute(query, (chat_id,))
        return [row['phone_number'] for row in cursor.fetchall()]

    def get_stats(self) -> dict:
        """
        Get overall database statistics

        Returns:
            Dictionary with counts
        """
        stats = {}

        # Total messages
        cursor = self.conn.execute(
            "SELECT COUNT(*) as count FROM message WHERE is_system_message = 0"
        )
        stats['total_messages'] = cursor.fetchone()['count']

        # Total conversations
        cursor = self.conn.execute(
            "SELECT COUNT(DISTINCT chat_id) as count FROM chat_message_join"
        )
        stats['total_conversations'] = cursor.fetchone()['count']

        # Total contacts
        cursor = self.conn.execute("SELECT COUNT(*) as count FROM handle")
        stats['total_contacts'] = cursor.fetchone()['count']

        # Date range
        cursor = self.conn.execute(
            "SELECT MIN(date) as min_date, MAX(date) as max_date FROM message WHERE date > 0"
        )
        row = cursor.fetchone()
        stats['first_message'] = self.convert_timestamp(row['min_date'])
        stats['last_message'] = self.convert_timestamp(row['max_date'])

        return stats

    def get_attachment_stats(self) -> dict:
        """
        Get attachment statistics
        
        Returns:
            Dictionary with attachment counts by type
        """
        stats = {}
        
        # Total attachments
        cursor = self.conn.execute("SELECT COUNT(*) as count FROM attachment")
        stats['total_attachments'] = cursor.fetchone()['count']
        
        # Attachments by MIME type
        cursor = self.conn.execute("""
            SELECT mime_type, COUNT(*) as count
            FROM attachment
            WHERE mime_type IS NOT NULL
            GROUP BY mime_type
            ORDER BY count DESC
        """)
        
        mime_counts = {}
        for row in cursor.fetchall():
            mime_counts[row['mime_type']] = row['count']
        
        stats['by_mime_type'] = mime_counts
        
        # Categorize into broader types
        stats['photos'] = sum(count for mime, count in mime_counts.items() if 'image' in mime)
        stats['videos'] = sum(count for mime, count in mime_counts.items() if 'video' in mime)
        stats['other'] = stats['total_attachments'] - stats['photos'] - stats['videos']
        
        return stats

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
