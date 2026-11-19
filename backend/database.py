"""The only gateway to Messages: mode=ro plus SQLite authorizer enforcement."""
import sqlite3
from pathlib import Path

DB_PATH = Path.home() / 'Library' / 'Messages' / 'chat.db'


def deny_writes(action, arg1, arg2, database, trigger):
    allowed = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_RECURSIVE}
    return sqlite3.SQLITE_OK if action in allowed else sqlite3.SQLITE_DENY


def connect(path=DB_PATH):
    conn = sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True, timeout=10)
    conn.execute('PRAGMA query_only=ON')
    conn.row_factory = sqlite3.Row
    conn.set_authorizer(deny_writes)
    return conn


def read_rows(path=DB_PATH):
    conn = connect(path)
    try:
        # Canonical chat per message prevents duplicate counting across joins.
        # style 43 is a group; style 45 is a direct chat. Participants are a fallback.
        query = '''
        WITH chosen AS (SELECT message_id,MIN(chat_id) chat_id FROM chat_message_join GROUP BY message_id),
        participants AS (SELECT chat_id,MIN(handle_id) partner,COUNT(DISTINCT handle_id) n FROM chat_handle_join GROUP BY chat_id)
        SELECT m.ROWID id,m.guid,m.date,m.is_from_me sent,m.handle_id actor,
          m.associated_message_type reaction_type,m.associated_message_guid target,
          m.associated_message_emoji reaction_emoji,m.cache_has_attachments media,
          c.ROWID chat_id,c.display_name chat_name,
          CASE WHEN c.style=43 OR p.n>1 THEN 1 ELSE 0 END is_group,
          COALESCE(h.id,ph.id) identifier
        FROM message m
        LEFT JOIN chosen j ON j.message_id=m.ROWID
        LEFT JOIN chat c ON c.ROWID=j.chat_id
        LEFT JOIN participants p ON p.chat_id=c.ROWID
        LEFT JOIN handle h ON h.ROWID=m.handle_id AND m.is_from_me=0
        LEFT JOIN handle ph ON ph.ROWID=p.partner
        WHERE m.date>0 AND COALESCE(m.is_system_message,0)=0
          AND COALESCE(m.item_type,0)=0 AND COALESCE(m.date_retracted,0)=0
          AND COALESCE(m.is_spam,0)=0
        ORDER BY m.date,m.ROWID
        '''
        return [dict(row) for row in conn.execute(query)]
    finally:
        conn.close()


def text_rows(ids, path=DB_PATH):
    conn = connect(path)
    try:
        for offset in range(0,len(ids),400):
            batch = ids[offset:offset+400]
            if batch:
                yield from conn.execute('SELECT text,attributedBody FROM message WHERE ROWID IN ('+','.join('?' for _ in batch)+')', batch)
    finally:
        conn.close()


def corpus_rows(path=DB_PATH):
    conn = connect(path)
    try:
        return conn.execute('SELECT ROWID id,text,attributedBody FROM message WHERE COALESCE(associated_message_type,0)=0').fetchall()
    finally:
        conn.close()


def attachment_rows(path=DB_PATH):
    """(message id, mime type) pairs. Older databases without attachment tables yield nothing."""
    conn = connect(path)
    try:
        return conn.execute('SELECT j.message_id,a.mime_type FROM message_attachment_join j JOIN attachment a ON a.ROWID=j.attachment_id').fetchall()
    except sqlite3.DatabaseError:
        return []
    finally:
        conn.close()
