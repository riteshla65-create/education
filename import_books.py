"""Import official chapter PDFs: python import_books.py [book-id] [--local directory]."""
import argparse
import json
from pathlib import Path
from urllib.request import Request, urlopen
from pypdf import PdfReader
from server import BOOKS, DATA, database

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('book', nargs='?', help='NCERT code, e.g. iemh1; omit for all books')
parser.add_argument('--local', type=Path, help='Folder containing chapter files such as iemh101.pdf')
args = parser.parse_args()
selected = [b for b in BOOKS if (not args.book or b['id'] == args.book) and not b.get('pending')]
if not selected:
    parser.error('Unknown book ID')
failed = False
for book in selected:
    count = len(book['chapters']) or 20
    for chapter in range(1, count + 1):
        filename = f"{book['id']}{chapter:02d}.pdf"
        destination = DATA / filename
        try:
            if args.local:
                destination = args.local / filename
                if not destination.exists():
                    continue
            elif not destination.exists():
                url = 'https://ncert.nic.in/textbook/pdf/' + filename
                request = Request(url, headers={'User-Agent': 'Classmate study library'})
                with urlopen(request, timeout=20) as response:
                    content = response.read(30_000_001)
                if len(content) > 30_000_000 or not content.startswith(b'%PDF'):
                    raise ValueError('Not a valid PDF or exceeds 30 MB')
                destination.write_bytes(content)
            pages = [(book['id'], chapter, page_number, (page.extract_text() or '').strip()) for page_number, page in enumerate(PdfReader(destination).pages, 1)]
            pages = [row for row in pages if row[3]]
            if not pages:
                raise ValueError('No extractable text in PDF')
            with database() as db:
                db.execute('DELETE FROM passages WHERE book=? AND chapter=?', (book['id'], chapter))
                db.executemany('INSERT INTO passages VALUES (?, ?, ?, ?)', pages)
            print(f'Imported {filename}: {len(pages)} pages')
        except Exception as exc:
            failed = True
            print(f'Unavailable {filename}: {type(exc).__name__}')
            if not args.local and chapter == 1:
                break
if failed:
    raise SystemExit(1)
