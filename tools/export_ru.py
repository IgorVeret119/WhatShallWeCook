"""Export completed recipe translations to a standalone UTF-8 CSV."""
import argparse
import csv
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from recipes import DB
from localization import TRANSLATIONS

def export_csv(output, source=DB, translations=TRANSLATIONS):
    output = Path(output).resolve()
    if output in (Path(source).resolve(), Path(translations).resolve(),
                  ROOT / 'recipes.csv', ROOT / 'data' / 'recipes.csv'):
        raise ValueError('Choose a new output file; source data must not be overwritten.')
    if not Path(source).exists() or not Path(translations).exists():
        raise ValueError('Recipe database or translation database is missing.')
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_suffix(output.suffix + '.part')
    count = 0
    try:
        with closing(sqlite3.connect(source)) as con:
            con.execute('ATTACH DATABASE ? AS ru', (str(translations),))
            total = con.execute('SELECT count(*) FROM recipes').fetchone()[0]
            cursor = con.execute('''SELECT r.id,r.name,t.name,r.category,t.category,
                r.ingredients,t.ingredients,r.quantities,r.instructions,t.instructions,
                r.calories,r.protein,r.fat,r.carbs,r.servings,r.minutes
                FROM recipes r JOIN ru.recipes t ON t.id=r.id ORDER BY r.id''')
            with partial.open('w', encoding='utf-8-sig', newline='') as handle:
                writer = csv.writer(handle)
                writer.writerow(['RecipeId','Name_en','Name_ru','Category_en','Category_ru',
                                 'Ingredients_en','Ingredients_ru','IngredientQuantities',
                                 'Instructions_en','Instructions_ru','Calories_kcal','Protein_g',
                                 'Fat_g','Carbohydrates_g','RecipeServings','TotalMinutes',
                                 'NutritionBasis'])
                for row in cursor:
                    writer.writerow([*row, 'per serving'])
                    count += 1
        partial.replace(output)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise
    return {'exported':count, 'dataset_count':total, 'output':str(output)}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'data' / 'recipes_ru.csv')
    args = parser.parse_args()
    try:
        print(export_csv(args.output))
        return 0
    except (OSError, ValueError, sqlite3.Error) as error:
        print(f'Export failed: {error}', file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
