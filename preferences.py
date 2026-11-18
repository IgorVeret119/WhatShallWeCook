"""Persistent ingredient preferences identified by an opaque browser profile cookie."""
import hashlib
import json
import re
import sqlite3
from contextlib import closing
from pathlib import Path

PREFERENCES_DB=Path(__file__).resolve().parent/'data'/'preferences.db'
FIELDS=('liked_products','excluded_products')

def profile_key(token):
    if not isinstance(token,str) or not re.fullmatch(r'[a-f0-9]{64}',token):
        raise ValueError('Некорректный профиль.')
    return hashlib.sha256(token.encode()).hexdigest()

def normalize_products(values):
    if not isinstance(values,list):
        raise ValueError('Передайте список продуктов.')
    result=[]
    for value in values:
        if not isinstance(value,str):
            raise ValueError('Название продукта должно быть текстом.')
        value=' '.join(value.strip().split())
        if not value or len(value)>80 or not re.search(r'[^\W\d_]',value):
            raise ValueError('Укажите название продукта длиной до 80 символов.')
        if value.casefold().replace('ё','е') not in {x.casefold().replace('ё','е') for x in result}:
            result.append(value)
    if len(result)>20:
        raise ValueError('В одном списке можно сохранить до 20 продуктов.')
    return result

def empty_preferences():
    return {key:[] for key in FIELDS}

def get_preferences(token,path=PREFERENCES_DB):
    key=profile_key(token)
    if not Path(path).exists():
        return empty_preferences()
    with closing(sqlite3.connect(path,timeout=10)) as con:
        if not con.execute("SELECT 1 FROM sqlite_master WHERE name='profiles'").fetchone():
            return empty_preferences()
        row=con.execute('SELECT liked_products,excluded_products FROM profiles WHERE profile_key=?',(key,)).fetchone()
        return {name:json.loads(value) for name,value in zip(FIELDS,row)} if row else empty_preferences()

def save_preferences(token,updates,path=PREFERENCES_DB):
    key=profile_key(token)
    if not isinstance(updates,dict) or not updates or set(updates)-set(FIELDS):
        raise ValueError('Укажите любимые или исключённые продукты.')
    normalized={field:normalize_products(values) for field,values in updates.items()}
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    with closing(sqlite3.connect(path,timeout=30)) as con:
        con.execute('''CREATE TABLE IF NOT EXISTS profiles(profile_key TEXT PRIMARY KEY,
            liked_products TEXT NOT NULL,excluded_products TEXT NOT NULL)''')
        with con:
            con.execute('BEGIN IMMEDIATE')
            row=con.execute('SELECT liked_products,excluded_products FROM profiles WHERE profile_key=?',(key,)).fetchone()
            result={name:json.loads(value) for name,value in zip(FIELDS,row)} if row else empty_preferences()
            result.update(normalized)
            from recipes import translate
            def canonical(value):return translate(value).replace('ё','е')
            excluded={canonical(value) for value in result['excluded_products']}
            for value in result['liked_products']:
                if canonical(value) in excluded:
                    raise ValueError(f'Продукт «{value}» не может быть одновременно любимым и исключённым.')
            con.execute('INSERT OR REPLACE INTO profiles VALUES (?,?,?)',
                        (key,*[json.dumps(result[field],ensure_ascii=False) for field in FIELDS]))
    return result

def merge_exclusions(preferences,extra=''):
    return ','.join(dict.fromkeys([*preferences['excluded_products'],*[x.strip() for x in extra.split(',') if x.strip()]]))
