# Classmate 3.0 — Maths, Science & SST

A colourful purple, teal and coral study portal with CSS 3D floating books, authentic NCERT title-page images, pointer tilt, click-to-open book animations, a pause button, and reduced-motion support. Only Mathematics, Science and Social Science appear in the library and tutor dropdown.

## Deploy the classroom demo

[Deploy to Render](https://render.com/deploy?repo=https%3A%2F%2Fgithub.com%2Friteshla65-create%2Fbirthday-wish%2Ftree%2Fcoderabbit%2Fclass-nine-study-portal%2F60a62aec)

The included `render.yaml` is a Render Blueprint (JSON syntax is valid YAML). It selects a free Python web service, installs the declared requirements, runs `python server.py`, and checks `/api/status`. Automatic deploys are off. The model defaults to `gpt-5.4-mini`; change it in Render if your API account needs a different Responses-compatible model.

1. Open the deployment link and sign in to your own Render account. If the repository is private, authorize access to this repository and branch.
2. Render reads the Blueprint. Enter your private `OPENAI_API_KEY` and choose `ADMIN_PASSWORD` when prompted. Keep both out of chat and GitHub.
3. Review the free service configuration and create the Blueprint. The external service and any API billing belong to your accounts.
4. Wait for deployment, open the service's public URL, and ask a short question in AI conversation mode. Verify an actual AI reply, then share that same URL with friends.
5. Admin Space uses the password you entered. Friends must opt in to activity sharing in Profile.

This is the current classroom prototype, using Python's standard-library HTTP server. Free hosting can sleep, and its local SQLite activity records can be lost on restart or deployment; the bundled NCERT text is restored on startup. For permanent activity storage, plan a persistent disk/database upgrade before relying on those records. There is no ten-student access lock in the current version. Public deployment and a live AI request still require your account setup; adding the Blueprint does not mean either has been completed.

## Open the HTML

Open `index.html` directly in a browser. The catalog, official title-page previews, CSS, JavaScript, 1008 extracted textbook pages and six short study notes are embedded. **Quick book replies now work without a server or AI key.** Saved books, profile and chapter checklists stay in browser storage. Full chapter PDF links require internet. Google Fonts are optional; fallback fonts work offline.

## Correct Class IX book editions

The official NCERT selector at https://ncert.nic.in/textbook.php was retrieved on 2026-10-14 and lists:

| Subject | Book | Code | Chapter PDFs |
| --- | --- | --- | --- |
| Maths | Ganita Manjari, Part I | iemh1 | 8 |
| Maths | Ganita Manjari, Part II | iemh2 | 6 |
| Science | Exploration | iesc1 | 13 |
| SST | Understanding Society: India and Beyond, Part I | iest1 | 9 |
| SST | Understanding Society: India and Beyond, Part II | iest2 | 6 |

All **42 chapter PDFs were downloaded and checked**, and their extractable text is bundled. Ganita Manjari Part II contains printed chapters 9–14; the site displays these numbers while using the correct part-specific PDF filenames. The previous version’s older chapter lists were replaced because NCERT now reuses its mathematics/science codes for the new books. Earlier progress checklists are preserved under their old browser key and are not applied to the new edition.

The user requested Parts III for Maths and SST. They are visible as **Not on NCERT yet** cards with a status page, and disabled in the tutor dropdown. No such part was found in the current official Class IX selector, so no URL, chapter list or release claim is invented. No student file upload is required: all currently available books are already attached from NCERT. The reader links directly to the official selector for each available book. The candidate third-part URLs iemh301.pdf/iest301.pdf and science-part-II iesc201.pdf were checked again and returned HTTP 404. Science is listed as one book; no extra science parts have been invented.

`book-sources.json` records the catalog source and PDF verification details. Extracted text can omit diagrams, notation and complex layouts. One SST chapter hit an extraction limit on embedded form content. Open the full PDF for diagrams and check the source when wording seems incomplete.

## Study Buddy

- **Quick reply:** searches only the selected book, recognizes common Hinglish/Hindi topic words, and returns a short source extract with chapter/PDF-page references. Six basic topics (coordinates, polynomials, atoms, cells, force and democracy) have clearly labelled, authored explanations and illustrative examples in Hinglish or English. These notes are not AI-generated replies or verbatim NCERT quotations.
- **AI conversation (default):** understands Hinglish, Hindi and English questions, gives worked solutions and uses recent user/assistant messages for follow-ups. General mode answers even when keyword retrieval finds no book extract, using model knowledge and labelling general explanations. A separate **Selected book only** option requires matching evidence. Related source extracts are displayed separately; they do not prove every AI statement.
- **New chat** clears session context. Enter sends; Shift+Enter adds a line. Questions allow 2000 characters; the server validates at most eight history messages, 1200 characters each and 6000 total. Conversations are kept in browser memory, not the classroom database. Only actual AI answers enter AI history; offline extracts are not presented as generated solutions.
- AI needs `OPENAI_API_KEY` and `OPENAI_MODEL` on the server. No credential is in HTML or the archive. Without this connection, arbitrary questions and worked solutions are unavailable; the app clearly labels its basic textbook fallback. Keyword retrieval can miss relevant pages and extracted text can omit diagrams/formulas. AI can make mistakes; check calculations and original pages.

### Book images

Five authentic page images are embedded in the HTML and packaged in `assets/covers/`. They are rendered from page 1 of the official NCERT preliminary PDFs (`<code>ps.pdf`), and labelled **NCERT page preview**. The selector's separate exterior-cover PNG links were unavailable for these new editions, so these images are title-page previews, not exterior cover artwork. Pending Part III uses a labelled placeholder. Image/source hashes and provenance are in `assets/covers/sources.json`. Students do not need to upload files. Rendering was performed with PyMuPDF 1.26.5; running the website does not need that package.

## Run the classroom server

Python 3.9+:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python server.py
```

Open http://localhost:3000. `PORT` changes the port. `CLASSMATE_DATA` points to a private persistent directory, default `data/`. A fresh default database is seeded from `book-passages.json`. The seed hash tracks edition changes without deleting classroom activity. When `CLASSMATE_DATA` is explicitly set, no bundled seed is loaded automatically; import the PDFs into that directory as needed.

Set `ADMIN_PASSWORD` privately before starting to enable administration. Friends enter their nickname in Profile and opt in to sharing chapter opens. Admin Space shows the latest 200 opens, not proof of reading. Names are self-reported. Reading while offline is not queued for later synchronization. Admin tokens stay in memory for one hour; five login attempts per IP are allowed in five minutes. Use a production server and HTTPS before publishing to the internet; Python’s standard-library server is a classroom development prototype.

### Optional AI configuration

Set `OPENAI_API_KEY` and `OPENAI_MODEL` privately in the server environment, choosing a Responses-compatible model available to your account. Restart the server, then select **AI conversation**. Provider charges may apply. Only the question, bounded recent chat history and relevant book passages are sent; student profiles and classroom activity are not included. Provider response storage is disabled. There is a six-request-per-minute AI limit per IP and a 35-second request timeout; failures fall back to textbook text.

Implementation follows the [official OpenAI text generation documentation](https://developers.openai.com/api/docs/guides/text). Live AI generation was not tested because no provider key/model is configured. Unit tests mock the Responses boundary and verify request/response handling. The inspected CodeRabbit Emulate v0.0.1 catalog has no OpenAI service.

## Refresh/import NCERT sources

```bash
.venv/bin/python import_books.py iemh1
.venv/bin/python import_books.py
# Or use official chapter PDFs already downloaded:
.venv/bin/python import_books.py --local /path/to/chapter-pdfs
```

Example filename: `iemh101.pdf`. Pending Parts III are excluded. Each chapter is replaced atomically. The full PDFs are not included in the project archive to keep it small; the archive includes their extracted text and official URLs. Locally downloaded PDFs in `data/` can be opened through `/books/<filename>.pdf` on the server. Private data and source files are not publicly served.

To refresh the standalone file after changing catalog/text/notes/PNG previews, run `python3 build_html.py`. The embedded source data escapes HTML tag characters so textbook content cannot terminate the script element. Update `book-passages.json` with verified imported text before rebuilding.

## Verify

```bash
.venv/bin/python -m unittest -v test_server.py test_tutor.py
```

Tests isolate database state and use synthetic identities, passwords, passages, and a synthetic PDF. They cover authentication, private paths, invalid/cross-origin requests, local import, book scoping, new catalog/source integrity, Hinglish/Hindi retrieval, missing AI configuration, and mocked AI requests. Browser checks additionally cover HTML-only replies, source references, subject filtering, saved books, progress, mobile layout and motion controls.
