"""Persistent favorites for the local recipe app, separate from imported datasets."""
import sqlite3
from contextlib import closing
from pathlib import Path

FAVORITES_DB=Path(__file__).resolve().parent/'data'/'favorites.db'

def attach_favorites(con,path=FAVORITES_DB):
    if not Path(path).exists():
        return False
    con.execute('ATTACH DATABASE ? AS saved_favorites',(str(path),))
    return bool(con.execute("SELECT 1 FROM saved_favorites.sqlite_master WHERE name='saved'").fetchone())

def set_favorite(recipe_id,saved,path=FAVORITES_DB):
    if not isinstance(recipe_id,int) or isinstance(recipe_id,bool) or recipe_id<1:
        raise ValueError('Некорректный номер рецепта.')
    if not isinstance(saved,bool):
        raise ValueError('Некорректное состояние избранного.')
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    with closing(sqlite3.connect(path,timeout=30)) as con:
        con.execute('''CREATE TABLE IF NOT EXISTS saved(
            recipe_id INTEGER PRIMARY KEY, added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)''')
        with con:
            if saved:
                con.execute('INSERT OR IGNORE INTO saved(recipe_id) VALUES (?)',(recipe_id,))
            else:
                con.execute('DELETE FROM saved WHERE recipe_id=?',(recipe_id,))
            count=con.execute('SELECT count(*) FROM saved').fetchone()[0]
    return {'recipe_id':recipe_id,'is_favorite':saved,'favorites_count':count}
