"""Re-embed current catalog and verified source text in the standalone HTML."""
import json
import base64
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parent
page=ROOT/'index.html'
text=page.read_text()
for marker,name,variable in [('CATALOG','catalog.json','BOOKS'),('PASSAGES','book-passages.json','PASSAGES'),('NOTES','study-notes.json','STUDY_NOTES')]:
    payload=json.dumps(json.loads((ROOT/name).read_text()),ensure_ascii=False,separators=(',',':')).replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
    replacement=f'/* {marker}_START */\nconst {variable}={payload};\n/* {marker}_END */'
    pattern=r'/\* '+marker+r'_START \*/.*?/\* '+marker+r'_END \*/'
    text,count=re.subn(pattern,lambda _:replacement,text,flags=re.S)
    if count!=1:raise ValueError('Missing or repeated embed marker: '+marker)
covers={p.stem:'data:image/png;base64,'+base64.b64encode(p.read_bytes()).decode() for p in (ROOT/'assets/covers').glob('*.png')}
text,count=re.subn(r'/\* COVERS_START \*/.*?/\* COVERS_END \*/',lambda _: '/* COVERS_START */\nconst COVERS='+json.dumps(covers,separators=(',',':'))+';\n/* COVERS_END */',text,flags=re.S)
if count!=1:raise ValueError('Missing covers marker')
page.write_text(text)
print('Embedded catalog and verified textbook passages.')
