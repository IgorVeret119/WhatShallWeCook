"""Recipe image URLs stored separately, so photo import does not block translation."""
import csv
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from urllib.parse import urlsplit

MEDIA_DB = Path(__file__).resolve().parent / 'data' / 'recipe_images.db'

def image_urls(value):
    from recipes import parse_list
    try:
        values = value if isinstance(value, list) else parse_list(value)
    except (ValueError, SyntaxError, TypeError):
        return []
    result = []
    for url in values:
        if not isinstance(url, str):
            continue
        url = url.strip()
        try:
            parsed = urlsplit(url)
            if parsed.scheme not in ('https', 'http') or not parsed.hostname or parsed.username or parsed.password:
                continue
        except ValueError:
            continue
        if url not in result:
            result.append(url)
        if len(result) == 5:
            break
    return result

def get_media(recipe_ids, path=MEDIA_DB):
    if not recipe_ids or not Path(path).exists():
        return {}
    with closing(sqlite3.connect(path, timeout=10)) as con:
        placeholders = ','.join('?' for _ in recipe_ids)
        rows = con.execute('SELECT recipe_id,images FROM photos WHERE recipe_id IN (' + placeholders + ')', list(recipe_ids))
        result = {row[0]:{'images':image_urls(json.loads(row[1]))} for row in rows}
        if con.execute("SELECT 1 FROM sqlite_master WHERE name='supplemental_photos'").fetchone():
            con.row_factory = sqlite3.Row
            for row in con.execute('SELECT * FROM supplemental_photos WHERE recipe_id IN ('+placeholders+')',list(recipe_ids)):
                if result.get(row['recipe_id'],{}).get('images'):
                    continue
                result[row['recipe_id']] = {'images':image_urls([row['image_url']]),
                    'photo_credit':{key:row[key] for key in ['author','source_url','license','license_url','kind']}}
        return result

def get_images(recipe_ids, path=MEDIA_DB):
    return {key:value['images'] for key,value in get_media(recipe_ids,path).items()}

def add_supplemental_photos(entries, destination=MEDIA_DB):
    """Apply a reviewed manifest; never replace the dataset's image references."""
    prepared = []
    for entry in entries:
        if len(image_urls([entry['image_url']])) != 1:
            raise ValueError('Image URL must be HTTP(S).')
        for key in ['source_url','license_url']:
            if len(image_urls([entry[key]])) != 1:
                raise ValueError('Invalid attribution URL.')
        if not entry['author'].strip() or not entry['license'].strip():
            raise ValueError('Image author and license are required.')
        if entry.get('kind') != 'illustration':
            raise ValueError('Supplemental photos must be identified as illustrations.')
        prepared.append(tuple(entry[key] for key in ['recipe_id','image_url','source_url','author','license','license_url','kind']))
    destination = Path(destination)
    destination.parent.mkdir(parents=True,exist_ok=True)
    with closing(sqlite3.connect(destination,timeout=30)) as con:
        con.execute('CREATE TABLE IF NOT EXISTS photos(recipe_id INTEGER PRIMARY KEY, images TEXT NOT NULL)')
        con.execute('''CREATE TABLE IF NOT EXISTS supplemental_photos(
            recipe_id INTEGER PRIMARY KEY,image_url TEXT NOT NULL,source_url TEXT NOT NULL,
            author TEXT NOT NULL,license TEXT NOT NULL,license_url TEXT NOT NULL,kind TEXT NOT NULL)''')
        with con:
            con.executemany('INSERT OR REPLACE INTO supplemental_photos VALUES (?,?,?,?,?,?,?)',prepared)
    return {'supplemental_photos_saved':len(prepared)}

def import_images(source, destination=MEDIA_DB):
    """Import image references atomically. Does not modify recipes or translations."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    csv.field_size_limit(10_000_000)
    count = seen = 0
    with open(source, encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        if not {'RecipeId','Images'}.issubset(reader.fieldnames or []):
            raise ValueError('CSV must contain RecipeId and Images columns.')
        with closing(sqlite3.connect(destination, timeout=30)) as con:
            con.execute('CREATE TABLE IF NOT EXISTS photos(recipe_id INTEGER PRIMARY KEY, images TEXT NOT NULL)')
            try:
                con.execute('DELETE FROM photos')
                batch = []
                for row in reader:
                    seen += 1
                    urls = image_urls(row['Images'])
                    if not urls:
                        continue
                    try:
                        recipe_id = int(row['RecipeId'])
                    except (ValueError, TypeError):
                        continue
                    batch.append((recipe_id,json.dumps(urls)))
                    count += 1
                    if len(batch) >= 1000:
                        con.executemany('INSERT OR REPLACE INTO photos VALUES (?,?)',batch)
                        batch.clear()
                    if count % 50000 == 0:
                        print(f'Image references imported: {count:,}',flush=True)
                if batch:
                    con.executemany('INSERT OR REPLACE INTO photos VALUES (?,?)',batch)
                con.commit()
            except BaseException:
                con.rollback()
                raise
    return {'recipes_with_images':count,'rows_read':seen}
