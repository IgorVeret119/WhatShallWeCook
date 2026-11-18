"""Add reviewed, attributed illustration photos without replacing dataset images."""
import argparse
import json
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from recipes import DB
from recipe_media import add_supplemental_photos

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,default=ROOT/'data'/'photo_additions.json')
    args=parser.parse_args()
    entries=json.loads(args.manifest.read_text(encoding='utf-8'))
    with closing(sqlite3.connect(DB)) as con:
        for entry in entries:
            row=con.execute('SELECT name FROM recipes WHERE id=?',(entry['recipe_id'],)).fetchone()
            if not row or row[0]!=entry['source_name']:
                raise ValueError(f'Recipe mismatch: {entry["recipe_id"]}')
    print(add_supplemental_photos(entries))

if __name__=='__main__':
    main()
