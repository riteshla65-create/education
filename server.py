"""Classmate: local NCERT passage search and consent-based reading activity."""
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from tutor import rank_passages, short_answer, ai_configured, explain_with_ai
from threading import Lock

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get('CLASSMATE_DATA', str(ROOT / 'data')))
DATA.mkdir(parents=True, exist_ok=True)
BOOKS = json.loads((ROOT / 'catalog.json').read_text())
BOOK_IDS = {b['id'] for b in BOOKS}
CHAPTER_LIMITS = {b['id']: len(b['chapters']) for b in BOOKS}
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', '')
SESSIONS = {}
LOGIN_ATTEMPTS = {}

def database():
    db = sqlite3.connect(DATA / 'classmate.sqlite')
    db.row_factory = sqlite3.Row
    return db

with database() as db:
    db.execute('CREATE TABLE IF NOT EXISTS activity (student TEXT, book TEXT, chapter INTEGER, opened TEXT DEFAULT CURRENT_TIMESTAMP)')
    db.execute('CREATE TABLE IF NOT EXISTS passages (book TEXT, chapter INTEGER, page INTEGER, text TEXT)')
    seed = ROOT / 'book-passages.json'
    db.execute('CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT)')
    if not os.environ.get('CLASSMATE_DATA') and seed.exists():
        source_hash = hashlib.sha256(seed.read_bytes()).hexdigest()
        previous = db.execute("SELECT value FROM metadata WHERE key='source_hash'").fetchone()
        if not previous or previous[0] != source_hash:
            rows = json.loads(seed.read_text())
            db.execute('DELETE FROM passages')
            db.executemany('INSERT INTO passages VALUES (?, ?, ?, ?)', [(row['book'], row['chapter'], row['page'], row['text']) for row in rows])
            db.execute("INSERT OR REPLACE INTO metadata VALUES ('source_hash', ?)", (source_hash,))



def search_passages(question, book):
    with database() as db:
        rows = db.execute('SELECT chapter, page, text FROM passages WHERE book = ?', (book,)).fetchall()
    matches = rank_passages(rows, question)
    chapter_numbers = next(b['chapterNumbers'] for b in BOOKS if b['id'] == book)
    for row in matches:
        if 1 <= row['chapter'] <= len(chapter_numbers): row['chapterLabel'] = chapter_numbers[row['chapter']-1]
    return matches

RATE_LOCK = Lock()
AI_ATTEMPTS = {}



class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, fmt, *args):
        # Avoid logging queries or student identity.
        pass

    def respond(self, data, status=200):
        payload = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(payload)

    def authorized(self):
        token = self.headers.get('Authorization', '').removeprefix('Bearer ')
        return SESSIONS.get(token, 0) > time.time()

    def do_HEAD(self):
        if urlparse(self.path).path not in {'/', '/index.html', '/catalog.json'}:
            self.send_response(404)
            self.end_headers()
            return
        return super().do_HEAD()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/api/status':
            with database() as db:
                indexed = [row[0] for row in db.execute('SELECT DISTINCT book FROM passages')]
            return self.respond({'online': True, 'indexed': indexed, 'adminConfigured': bool(ADMIN_PASSWORD), 'aiConfigured': ai_configured()})
        if path == '/api/activity':
            if not self.authorized():
                return self.respond({'error': 'Admin login required.'}, 401)
            with database() as db:
                rows = [dict(row) for row in db.execute('SELECT * FROM activity ORDER BY opened DESC, rowid DESC LIMIT 200')]
            return self.respond({'activity': rows})
        if path.startswith('/books/'):
            filename = path.removeprefix('/books/')
            match = re.fullmatch(r'([a-z0-9]+)([0-9]{2})\.pdf', filename)
            if not match or match[1] not in BOOK_IDS or not (DATA / filename).is_file():
                return self.respond({'error': 'PDF unavailable. Use the official NCERT link.'}, 404)
            payload = (DATA / filename).read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'application/pdf')
            self.send_header('Content-Length', str(len(payload)))
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(payload)
            return
        # Explicit allowlist protects database, Python source and hidden files.
        if path not in {'/', '/index.html', '/catalog.json', '/static/hero.svg'}:
            return self.respond({'error': 'Not found.'}, 404)
        return super().do_GET()

    def do_POST(self):
        origin = self.headers.get('Origin')
        if origin and urlparse(origin).netloc != self.headers.get('Host'):
            return self.respond({'error': 'Cross-origin request denied.'}, 403)
        try:
            size = int(self.headers.get('Content-Length', 0))
            if size < 1 or size > 32768:
                return self.respond({'error': 'Invalid request size.'}, 400)
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict):
                raise ValueError()
        except (ValueError, json.JSONDecodeError):
            return self.respond({'error': 'Invalid request.'}, 400)
        path = urlparse(self.path).path
        if path == '/api/login':
            if not ADMIN_PASSWORD:
                return self.respond({'error': 'Set ADMIN_PASSWORD on the server to enable admin access.'}, 503)
            key = self.client_address[0]
            now = time.time()
            attempts = [stamp for stamp in LOGIN_ATTEMPTS.get(key, []) if stamp > now - 300]
            LOGIN_ATTEMPTS[key] = attempts
            if len(attempts) >= 5:
                return self.respond({'error': 'Too many attempts. Try again in 5 minutes.'}, 429)
            attempts.append(now)
            supplied = data.get('password', '')
            if not isinstance(supplied, str) or not hmac.compare_digest(hashlib.sha256(supplied.encode()).digest(), hashlib.sha256(ADMIN_PASSWORD.encode()).digest()):
                return self.respond({'error': 'Incorrect password.'}, 401)
            token = secrets.token_urlsafe(32)
            SESSIONS[token] = now + 3600
            return self.respond({'token': token})
        if path == '/api/activity':
            name, book, chapter = data.get('student'), data.get('book'), data.get('chapter')
            if not isinstance(name, str) or not 1 <= len(name.strip()) <= 60 or not isinstance(book, str) or book not in BOOK_IDS or type(chapter) is not int or not 1 <= chapter <= CHAPTER_LIMITS[book]:
                return self.respond({'error': 'Invalid reading activity.'}, 400)
            with database() as db:
                db.execute('INSERT INTO activity (student, book, chapter) VALUES (?, ?, ?)', (name.strip(), book, chapter))
            return self.respond({'saved': True})
        if path == '/api/ask':
            question, book = data.get('question', ''), data.get('book')
            if not isinstance(question, str) or not 3 <= len(question.strip()) <= 2000 or not isinstance(book, str) or book not in BOOK_IDS:
                return self.respond({'error': 'Choose a book and enter a question (3–2000 characters).'}, 400)
            mode = data.get('mode', 'quick')
            language = data.get('language', 'Hinglish')
            if mode not in ('quick', 'ai') or language not in ('Hinglish', 'English', 'Hindi'):
                return self.respond({'error': 'Invalid tutor mode or language.'}, 400)
            history, scope = data.get('history', []), data.get('scope', 'general')
            if scope not in ('general', 'book') or not isinstance(history, list) or len(history) > 8:
                return self.respond({'error': 'Invalid conversation or source setting.'}, 400)
            if any(not isinstance(item, dict) or item.get('role') not in ('user', 'assistant') or not isinstance(item.get('content'), str) or not 1 <= len(item['content']) <= 1200 for item in history):
                return self.respond({'error': 'Invalid conversation messages.'}, 400)
            if sum(len(item['content']) for item in history) > 6000:
                return self.respond({'error': 'Conversation is too long. Start a new chat.'}, 400)
            history = [{'role':item['role'], 'content':item['content']} for item in history]
            search_question = question
            if re.match(r'^(aur|example|again|simple|asaan|easy|samjhao|explain again|dobara|continue|isko|isse)', question, re.I):
                previous = next((item['content'] for item in reversed(history) if item['role'] == 'user'), '')
                search_question = previous + ' ' + question
            matches = search_passages(search_question, book)
            message = 'Book se short answer — source extracts below.' if matches else 'Is topic ka matching text nahi mila. Book ka keyword likho; main bina source ke answer guess nahi karunga.'
            answer = short_answer(question, matches)
            answer_mode = 'extract'
            if mode == 'ai':
                if not ai_configured():
                    message = 'AI explanation is not connected. Here is a quick answer from your book.'
                    if re.search(r'\b(solve|calculate|solution|numerical)\b|\d.*[=+*/^−-]', question, re.I):
                        answer = ''
                        message = 'AI is not connected. Worked solutions need the classroom AI connection. Related textbook pages, if found, are listed below.'
                elif scope == 'book' and not matches:
                    message = 'Book-only mode: matching evidence nahi mila. Specific topic ya chapter ka keyword likho.'
                else:
                    now = time.time()
                    key = self.client_address[0]
                    with RATE_LOCK:
                        attempts = [stamp for stamp in AI_ATTEMPTS.get(key, []) if stamp > now - 60]
                        AI_ATTEMPTS[key] = attempts
                        limited = len(attempts) >= 6
                        if not limited: attempts.append(now)
                    if limited:
                        return self.respond({'error': 'AI limit reached. Try again in a minute or use Quick reply.'}, 429)
                    try:
                        answer = explain_with_ai(question, next(b['title'] for b in BOOKS if b['id'] == book), matches, language, history, scope)
                        answer_mode = 'ai'
                        message = 'AI tutor · Book-only explanation; check the source pages.' if scope == 'book' else 'AI tutor · General knowledge may be used. Related NCERT extracts below, when available.'
                    except Exception:
                        message = 'AI reply is unavailable right now. Here is the quick textbook answer.'
            return self.respond({'matches': matches, 'message': message, 'answer': answer, 'mode': answer_mode})
        return self.respond({'error': 'Not found.'}, 404)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    print('Classmate ready at http://0.0.0.0:' + str(port), flush=True)
    ThreadingHTTPServer(('0.0.0.0', port), Handler).serve_forever()
