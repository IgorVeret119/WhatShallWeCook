"""Persistent Russian recipe translations, separate from the source dataset."""
import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TRANSLATIONS = ROOT / 'data' / 'translations.db'

def initialize(path=TRANSLATIONS):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as con:
        con.executescript('''
        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY, fingerprint TEXT NOT NULL,
            name TEXT NOT NULL, category TEXT NOT NULL,
            ingredients TEXT NOT NULL, instructions TEXT NOT NULL,
            ingredient_text TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS texts(source TEXT PRIMARY KEY, translated TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS origins(id INTEGER PRIMARY KEY, method TEXT NOT NULL);
        CREATE VIRTUAL TABLE IF NOT EXISTS search USING fts5(name, ingredient_text, category);
        ''')

def fingerprint(recipe):
    fields = [recipe[k] for k in ('name', 'category', 'ingredients', 'instructions')]
    return hashlib.sha256(json.dumps(fields, ensure_ascii=False).encode()).hexdigest()

def translate_recipe(recipe, translator, path=TRANSLATIONS, *, method='machine', overwrite=False,
                     use_cache=True):
    """Commit each complete recipe atomically. Interrupted runs resume safely."""
    con = sqlite3.connect(path, timeout=30)
    try:
        signature = fingerprint(recipe)
        old = con.execute('SELECT fingerprint FROM recipes WHERE id=?', (recipe['id'],)).fetchone()
        if old and old[0] == signature and not overwrite:
            return False

        def text(source):
            if not source:
                return source
            old_text = con.execute('SELECT translated FROM texts WHERE source=?', (source,)).fetchone() if use_cache else None
            if old_text:
                return old_text[0]
            value = translator(source)
            if not isinstance(value, str) or not value.strip():
                raise ValueError('Translation returned empty text')
            if use_cache:
                con.execute('INSERT OR REPLACE INTO texts VALUES (?,?)', (source, value))
            return value

        name = text(recipe['name'])
        category = text(recipe['category'] or '')
        ingredients = [text(x) for x in recipe['ingredients']]
        instructions = [text(x) for x in recipe['instructions']]
        ingredient_text = ' | '.join(x for x in ingredients if x).casefold()
        con.execute('INSERT OR REPLACE INTO recipes VALUES (?,?,?,?,?,?,?)', (
            recipe['id'], signature, name, category,
            json.dumps(ingredients, ensure_ascii=False), json.dumps(instructions, ensure_ascii=False),
            ingredient_text))
        con.execute('DELETE FROM search WHERE rowid=?', (recipe['id'],))
        con.execute('INSERT INTO search(rowid,name,ingredient_text,category) VALUES (?,?,?,?)',
                    (recipe['id'], name, ingredient_text, category))
        con.execute('INSERT OR REPLACE INTO origins VALUES (?,?)', (recipe['id'], method))
        con.commit()
        return True
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()

def attach(con, path=TRANSLATIONS):
    if not Path(path).exists():
        return False
    con.execute('ATTACH DATABASE ? AS localized', (str(path),))
    return True

def localize(item, language, con):
    """Preserve originals and leave untranslated recipes explicitly in English."""
    item['content_language'] = 'en'
    if language != 'ru':
        return item
    row = con.execute('SELECT * FROM localized.recipes WHERE id=?', (item['id'],)).fetchone()
    if not row:
        return item
    for key in ('name', 'category', 'ingredients', 'instructions'):
        if key in item:
            item[key + '_original'] = item[key]
            item[key] = json.loads(row[key]) if key in ('ingredients', 'instructions') else row[key]
    item['content_language'] = 'ru'
    has_origins = con.execute("SELECT 1 FROM localized.sqlite_master WHERE name='origins'").fetchone()
    origin = con.execute('SELECT method FROM localized.origins WHERE id=?', (item['id'],)).fetchone() if has_origins else None
    item['translation_method'] = origin[0] if origin else 'machine'
    return item
