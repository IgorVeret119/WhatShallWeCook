"""Food.com CSV ingestion and deterministic SQLite search. Standard library only."""
import ast
import csv
import json
import math
import re
import sqlite3
from pathlib import Path
from localization import TRANSLATIONS, attach, localize
from recipe_media import MEDIA_DB, get_media
from favorites import FAVORITES_DB, attach_favorites

ROOT = Path(__file__).resolve().parent
DB = ROOT / 'data' / 'recipes.db'
SOURCE = 'https://www.kaggle.com/datasets/irkaal/foodcom-recipes-and-reviews'
MIRROR = 'https://huggingface.co/datasets/untitledwebsite123/food-recipes'
DOWNLOAD = MIRROR + '/resolve/main/recipes.csv?download=true'

# A small, explicit dictionary, not a language model or automatic translation.
ALIASES = {
    'курица': 'chicken', 'курицей': 'chicken', 'курицу': 'chicken',
    'рис': 'rice', 'рисом': 'rice', 'грибы': 'mushroom', 'грибов': 'mushroom',
    'говядина': 'beef', 'свинина': 'pork', 'рыба': 'fish', 'лосось': 'salmon',
    'яйцо': 'egg', 'яйца': 'egg', 'молоко': 'milk', 'сыр': 'cheese',
    'картофель': 'potato', 'картошка': 'potato', 'помидор': 'tomato',
    'помидоры': 'tomato', 'томаты': 'tomato', 'лук': 'onion',
    'чеснок': 'garlic', 'морковь': 'carrot', 'суп': 'soup',
    'салат': 'salad', 'паста': 'pasta', 'овсянка': 'oat',
    'банан': 'banana', 'яблоко': 'apple', 'творог': 'cottage cheese',
    'брокколи': 'broccoli', 'индейка': 'turkey', 'шоколад': 'chocolate',
}

def translate(text):
    return ' '.join(ALIASES.get(t, t) for t in re.findall(r'[^\W_]+', text.casefold()))

def parse_list(value):
    """Read JSON lists and the R c(\"...\", NA, ...) serialization in Food.com CSV."""
    if not value or value in ('NA', 'character(0)'):
        return []
    if isinstance(value, list):
        return value
    value = value.strip()
    if value.startswith('['):
        return json.loads(value)
    if not value.startswith('c('):
        if value.startswith('"') and value.endswith('"'):
            try:
                return [ast.literal_eval(value)]
            except (SyntaxError, ValueError):
                # Some scalar R exports contain unescaped quotes or literal
                # newlines. Preserve the text instead of discarding the recipe.
                return [value[1:-1]]
        return [value]
    if not value.endswith(')'):
        raise ValueError('Incomplete R list')
    text = value[2:-1]
    # Tokenize strings before handling NA, so quoted ingredient names stay intact.
    pattern = re.compile(r'\s*("(?:\\.|[^"\\])*"|NA)\s*(,|$)', re.S)
    result, pos = [], 0
    while pos < len(text):
        match = pattern.match(text, pos)
        if not match:
            raise ValueError('Invalid R list')
        token = match.group(1)
        result.append(None if token == 'NA' else ast.literal_eval(token))
        pos = match.end()
    return result

def number(value):
    try:
        n = float(value)
        return n if math.isfinite(n) and n >= 0 else None
    except (ValueError, TypeError):
        return None

def minutes(value):
    if not value:
        return None
    match = re.fullmatch(r'P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?', value)
    if not match or not any(match.groups()):
        return None
    d, h, m, s = [int(x or 0) for x in match.groups()]
    return d * 1440 + h * 60 + m + s / 60

def connect(path=DB):
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    return con

def import_csv(source, destination=DB):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = destination.with_suffix('.building.db')
    if staging.exists():
        staging.unlink()
    csv.field_size_limit(10_000_000)
    con = connect(staging)
    accepted = rejected = 0
    try:
        con.executescript('''
        CREATE TABLE recipes (
            id INTEGER PRIMARY KEY, name TEXT NOT NULL, category TEXT,
            calories REAL, protein REAL, fat REAL, carbs REAL, minutes REAL,
            servings REAL, ingredients TEXT NOT NULL, quantities TEXT NOT NULL,
            instructions TEXT NOT NULL, ingredient_text TEXT NOT NULL
        );
        CREATE VIRTUAL TABLE search USING fts5(name, ingredient_text, category,
            content='recipes', content_rowid='id', tokenize='unicode61');
        CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT);
        ''')
        with open(source, encoding='utf-8-sig', newline='') as handle:
            reader = csv.DictReader(handle)
            required = {'RecipeId', 'Name', 'Calories', 'ProteinContent', 'FatContent',
                        'CarbohydrateContent', 'RecipeIngredientParts', 'RecipeInstructions'}
            if not required.issubset(reader.fieldnames or []):
                raise ValueError('Expected Food.com Recipes and Reviews CSV. Missing: ' +
                                 ', '.join(sorted(required - set(reader.fieldnames or []))))
            for row in reader:
                try:
                    ingredients = parse_list(row['RecipeIngredientParts'])
                    quantities = parse_list(row.get('RecipeIngredientQuantities'))
                    instructions = parse_list(row['RecipeInstructions'])
                    recipe_id = int(row['RecipeId'])
                    name = row['Name'].strip()
                    if not name or not ingredients:
                        raise ValueError('Empty recipe')
                    nutrition = [number(row[k]) for k in
                                 ('Calories', 'ProteinContent', 'FatContent', 'CarbohydrateContent')]
                    values = (recipe_id, name, row.get('RecipeCategory', ''), *nutrition,
                              minutes(row.get('TotalTime')), number(row.get('RecipeServings')),
                              json.dumps(ingredients, ensure_ascii=False), json.dumps(quantities),
                              json.dumps(instructions, ensure_ascii=False),
                              ' | '.join(str(x) for x in ingredients if x).casefold())
                    con.execute('INSERT INTO recipes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)', values)
                    accepted += 1
                    if accepted % 10000 == 0:
                        con.commit()
                        print(f'Imported {accepted:,}; skipped {rejected:,}', flush=True)
                except (ValueError, TypeError, SyntaxError, sqlite3.IntegrityError):
                    rejected += 1
        if accepted == 0:
            raise ValueError('No valid recipes: existing database was preserved.')
        con.execute("INSERT INTO search(search) VALUES ('rebuild')")
        con.executescript('''CREATE INDEX nutrition_idx ON recipes(calories, protein);
                            CREATE INDEX time_idx ON recipes(minutes);''')
        con.executemany('INSERT INTO metadata VALUES (?,?)', [
            ('source', SOURCE), ('mirror', MIRROR), ('basis', 'per serving, as provided by Food.com'),
            ('count', str(accepted)), ('skipped', str(rejected)),
        ])
        con.commit()
    except BaseException:
        con.close()
        staging.unlink(missing_ok=True)
        raise
    con.close()
    staging.replace(destination)
    return {'imported': accepted, 'skipped': rejected}

def like_literal(value):
    return value.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')

def search(params, path=DB, translations_path=TRANSLATIONS, media_path=MEDIA_DB, favorites_path=FAVORITES_DB):
    """All constraints use bound parameters. No natural-language constraint parsing."""
    if not Path(path).exists():
        return {'items': [], 'total': 0, 'dataset_count': 0, 'page': 1, 'favorites_count':0}
    where, args = [], []
    has_translations = Path(translations_path).exists()
    query = translate(params.get('q', ''))
    terms = query.split()
    if len(terms) > 20:
        raise ValueError('Не больше 20 слов в запросе.')
    join = ''
    if terms:
        expression = ' AND '.join('"' + word + '"*' for word in terms)
        if has_translations:
            raw_terms = re.findall(r'[^\W_]+', params.get('q', '').casefold().replace('ё', 'е'))
            raw_expression = ' AND '.join('"' + word + '"*' for word in raw_terms)
            where.append('r.id IN (SELECT rowid FROM search WHERE search MATCH ? '
                         'UNION SELECT rowid FROM localized.search WHERE search MATCH ?)')
            args.extend((expression, raw_expression))
        else:
            join = ' JOIN search ON search.rowid = r.id '
            where.append('search MATCH ?')
            args.append(expression)
    for key in ('include', 'exclude'):
        raw_terms = [x.strip() for x in params.get(key, '').split(',') if x.strip()]
        if len(raw_terms) > 20:
            raise ValueError('Не больше 20 ингредиентов в поле.')
        for ingredient in raw_terms:
            normalized = translate(ingredient)
            if not normalized:
                raise ValueError('Укажите название ингредиента.')
            match = "r.ingredient_text LIKE ? ESCAPE '\\'"
            args.append('%' + like_literal(normalized) + '%')
            if has_translations:
                match += (" OR r.id IN (SELECT id FROM localized.recipes "
                          "WHERE ingredient_text LIKE ? ESCAPE '\\')")
                args.append('%' + like_literal(ingredient.casefold()) + '%')
            where.append(('NOT ' if key == 'exclude' else '') + '(' + match + ')')
    for field in ('calories', 'protein', 'fat', 'carbs'):
        for bound, operator in [('min', '>='), ('max', '<=')]:
            key = f'{bound}_{field}'
            raw = params.get(key, '')
            if raw != '':
                n = number(raw)
                if n is None:
                    raise ValueError('Числовые фильтры должны быть конечными и неотрицательными.')
                where.append(f'r.{field} {operator} ?')
                args.append(n)
        lo, hi = params.get('min_' + field, ''), params.get('max_' + field, '')
        if lo != '' and hi != '' and float(lo) > float(hi):
            raise ValueError('Минимум не может быть больше максимума.')
    if params.get('max_minutes', '') != '':
        n = number(params['max_minutes'])
        if n is None:
            raise ValueError('Некорректное время приготовления.')
        where.append('r.minutes <= ?')
        args.append(n)
    try:
        page = max(1, min(100000, int(params.get('page', '1'))))
    except (ValueError, TypeError):
        raise ValueError('Некорректная страница.')
    order = {'name': 'r.name COLLATE NOCASE, r.id', 'calories': 'r.calories IS NULL, r.calories, r.id',
             'protein': 'r.protein IS NULL, r.protein DESC, r.id',
             'time': 'r.minutes IS NULL, r.minutes, r.id',
             'relevance': 'bm25(search), r.id' if terms and not has_translations else 'r.id'}.get(params.get('sort'), 'r.id')
    # Compare relative deviations so calories do not outweigh grams of macros.
    # Floors make zero and small targets useful without division by zero.
    targets={}
    distance_terms, distance_args, missing = [], [], []
    for field,floor in [('calories',100),('protein',10),('fat',5),('carbs',10)]:
        raw=params.get('target_'+field,'')
        if raw=='':
            continue
        target=number(raw)
        if target is None or target>1_000_000:
            raise ValueError('Цели КБЖУ должны быть числами от 0 до 1000000.')
        targets[field]=target
        scale=max(target,floor)
        distance_terms.append(f'((r.{field}-?)/?)*((r.{field}-?)/?)')
        distance_args.extend([target,scale,target,scale])
        missing.append(f'r.{field} IS NULL')
    distance_select=''
    if targets:
        distance_select=', CASE WHEN '+' OR '.join(missing)+' THEN NULL ELSE ('+'+'.join(distance_terms)+f')/{float(len(targets))} END AS nutrition_distance'
    preference_args=[]
    preferred=[value.strip() for value in params.get('preferred','').split(',') if value.strip()]
    if len(preferred)>20:
        raise ValueError('Не больше 20 любимых продуктов.')
    if preferred and params.get('sort','relevance') in ('relevance','nutrition'):
        def expression(values):
            groups=[]
            for value in values:
                words=re.findall(r'[^\W_]+',value.casefold())
                if words:groups.append('('+' AND '.join('"'+w+'"*' for w in words)+')')
            return ' OR '.join(groups)
        english=expression([translate(value) for value in preferred])
        russian=expression(preferred)
        if english:
            hit='SELECT rowid FROM search WHERE search MATCH ?'
            preference_args.append(english)
            if has_translations:
                hit+=' UNION SELECT rowid FROM localized.search WHERE search MATCH ?'
                preference_args.append(russian)
            order='CASE WHEN r.id IN ('+hit+') THEN 0 ELSE 1 END, '+order
    if targets and params.get('sort','nutrition')=='nutrition':
        # Preferences break equal distances; they never displace a closer recipe.
        order='nutrition_distance IS NULL, nutrition_distance, '+order
    con = connect(path)
    try:
        if has_translations:
            attach(con, translations_path)
        has_favorites=attach_favorites(con,favorites_path)
        if params.get('favorites_only')=='1':
            where.append('r.id IN (SELECT recipe_id FROM saved_favorites.saved)' if has_favorites else '0')
        tail = ' FROM recipes r ' + join + (' WHERE ' + ' AND '.join(where) if where else '')
        total = con.execute('SELECT count(*)' + tail, args).fetchone()[0]
        rows = con.execute('SELECT r.id,r.name,r.category,r.calories,r.protein,r.fat,r.carbs,r.minutes,'
                           'r.servings,r.ingredients,r.quantities,r.instructions'+distance_select
                           + tail + ' ORDER BY ' + order + ' LIMIT 24 OFFSET ?',
                           [*distance_args,*args,*preference_args, (page - 1) * 24]).fetchall()
        count = con.execute("SELECT value FROM metadata WHERE key='count'").fetchone()[0]
        items = [dict(r) for r in rows]
        saved_ids=set()
        favorites_count=0
        if has_favorites:
            saved_ids={row[0] for row in con.execute('SELECT recipe_id FROM saved_favorites.saved')}
            favorites_count=con.execute('SELECT count(*) FROM saved_favorites.saved f JOIN recipes r ON r.id=f.recipe_id').fetchone()[0]
        pictures = get_media([item['id'] for item in items],media_path)
        for item in items:
            if targets:
                distance=item.pop('nutrition_distance')
                item['nutrition_deviation_percent']=round(math.sqrt(distance)*100) if distance is not None else None
            item['is_favorite']=item['id'] in saved_ids
            for field in ('ingredients','quantities','instructions'):
                item[field] = json.loads(item[field])
            item.update(pictures.get(item['id'],{'images':[]}))
        translated_count = 0
        if has_translations:
            items = [localize(item, params.get('lang', 'ru'), con) for item in items]
            translated_count = con.execute('SELECT count(*) FROM localized.recipes').fetchone()[0]
        return {'items': items, 'total': total, 'dataset_count': int(count), 'page': page,
                'translated_count': translated_count,'favorites_count':favorites_count}
    finally:
        con.close()

def detail(recipe_id, path=DB, language='ru', translations_path=TRANSLATIONS, media_path=MEDIA_DB):
    if not Path(path).exists():
        return None
    con = connect(path)
    try:
        row = con.execute('SELECT * FROM recipes WHERE id=?', (recipe_id,)).fetchone()
        if not row:
            return None
        item = dict(row)
        for field in ('ingredients', 'quantities', 'instructions'):
            item[field] = json.loads(item[field])
        item.update(get_media([recipe_id],media_path).get(recipe_id,{'images':[]}))
        if attach(con, translations_path):
            item = localize(item, language, con)
        item['url'] = f'https://www.food.com/recipe/{item["id"]}'
        return item
    finally:
        con.close()
