"""Read-only bounded history pages. Cursors are positions, never tool authority."""
import base64
import binascii
import json
import math

MAX_PAGE = 100
DEFAULT_PAGE = 50
MAX_CURSOR = 2048
MAX_EXPORT_MESSAGES = 5000
MAX_EXPORT_BYTES = 8 * 1024**2
TASK_COLUMNS = "id,conversation,mode,status,model,created,profile"
COLUMNS = {
    "conversations": "id,title,created",
    "messages": "id,conversation,role,content,created,metrics",
    "tasks": TASK_COLUMNS,
}


def encode_cursor(domain, row):
    value = [1, *domain, row["created"], row["_row"]]
    return base64.urlsafe_b64encode(json.dumps(value, separators=(",", ":")).encode()).decode().rstrip("=")


def decode_cursor(cursor, domain):
    if not isinstance(cursor, str) or not 1 <= len(cursor) <= MAX_CURSOR:
        raise ValueError("Invalid history cursor; reload the first page")
    try:
        data = base64.b64decode(cursor + "=" * (-len(cursor) % 4), altchars=b"-_", validate=True)
        value = json.loads(data)
        if (not isinstance(value, list) or len(value) != 7 or type(value[0]) is not int
                or value[0] != 1 or value[1:5] != list(domain)
                or type(value[5]) not in (int, float) or not math.isfinite(value[5])
                or type(value[6]) is not int or not 1 <= value[6] < 2**63):
            raise ValueError
    except (ValueError, TypeError, OverflowError, binascii.Error, UnicodeError) as exc:
        raise ValueError("Invalid history cursor; reload the first page") from exc
    return value[5:]


def page(store, kind, *, conversation="", query="", cursor=None, limit=DEFAULT_PAGE):
    if kind not in COLUMNS or type(limit) is not int or not 1 <= limit <= MAX_PAGE:
        raise ValueError("History page size must be between 1 and 100")
    if (not isinstance(conversation, str) or len(conversation) > 128
            or not isinstance(query, str) or len(query) > 120
            or (kind == "messages" and not conversation)
            or (kind == "conversations" and conversation) or (kind != "conversations" and query)):
        raise ValueError("Invalid history scope or search")
    domain = (store.identity, kind, conversation, query)
    position = decode_cursor(cursor, domain) if cursor is not None else None
    clauses, args = [], []
    if conversation:
        clauses.append("conversation=?")
        args.append(conversation)
    if query:
        clauses.append("history_match(title,?)")
        args.append(query)
    if position:
        clauses.append("(created,rowid)<(?,?)")
        args.extend(position)
    # kind/columns are trusted constants; all caller values use SQL parameters.
    sql = f"SELECT rowid AS _row,{COLUMNS[kind]} FROM {kind}"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY created DESC,rowid DESC LIMIT ?"
    args.append(limit + 1)
    with store.connection() as db:
        if conversation and not db.execute("SELECT 1 FROM conversations WHERE id=?", (conversation,)).fetchone():
            raise KeyError("Conversation not found")
        db.create_function("history_match", 2, lambda title, text: text.casefold() in title.casefold(), deterministic=True)
        rows = [dict(row) for row in db.execute(sql, args)]
        more = len(rows) > limit
        rows = rows[:limit]
        next_cursor = encode_cursor(domain, rows[-1]) if more else None
        if kind == "messages" and rows:
            attachments = {}
            for row in db.execute("SELECT id,message,name,mime,size FROM attachments WHERE conversation=? "
                                  f"AND message IN ({','.join('?' for _ in rows)}) ORDER BY rowid",
                                  [conversation, *[row["id"] for row in rows]]):
                attachments.setdefault(row["message"], []).append({
                    key: row[key] for key in ("id", "name", "mime", "size")})
            for row in rows:
                row["metrics"] = json.loads(row["metrics"]) if row["metrics"] else None
                row["attachments"] = attachments.get(row["id"], [])
    for row in rows:
        row.pop("_row")
    if kind == "messages":
        rows.reverse()  # Each older page is suitable for prepending to the visible transcript.
    return {"items": rows, "next": next_cursor, "limit": limit,
            "order": "oldest_first" if kind == "messages" else "newest_first"}


def export_markdown(store, conversation):
    """One consistent visible transcript; reject limits before returning any export."""
    chunks, size, count = [], 0, 0

    def append(text):
        nonlocal size
        size += len(text.encode('utf-8'))
        if size > MAX_EXPORT_BYTES:
            raise ValueError('Conversation export exceeds the 8 MiB UTF-8 limit; no partial export was produced')
        chunks.append(text)

    with store.connection() as db:
        db.execute('BEGIN')  # Title, transcript and attachment metadata share one WAL snapshot.
        chat = db.execute('SELECT title FROM conversations WHERE id=?', (conversation,)).fetchone()
        if chat is None:
            raise KeyError('Conversation not found')
        append(f"# {chat['title']}\n\n")
        for row in db.execute('SELECT id,role,content FROM messages WHERE conversation=? '
                              'ORDER BY created,rowid LIMIT ?', (conversation, MAX_EXPORT_MESSAGES + 1)):
            count += 1
            if count > MAX_EXPORT_MESSAGES:
                raise ValueError('Conversation export exceeds the 5,000-message limit; no partial export was produced')
            append(f"## {'You' if row['role'] == 'user' else 'Local Agent'}\n\n{row['content']}\n\n")
            for attachment in db.execute('SELECT name,size FROM attachments WHERE conversation=? AND message=? '
                                          'ORDER BY rowid', (conversation, row['id'])):
                append(f"Attachment: {attachment['name']} ({math.ceil(attachment['size'] / 1024)} KiB)\n")
            append('\n')
    return {'markdown': ''.join(chunks), 'message_count': count, 'bytes': size, 'complete': True,
            'max_messages': MAX_EXPORT_MESSAGES, 'max_bytes': MAX_EXPORT_BYTES}
