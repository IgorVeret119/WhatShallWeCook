"""Translate Food.com to Russian locally using Argos Translate, with resume support."""
import argparse
import json
import sqlite3
import sys
import subprocess
import time
import os
import urllib.request
import zipfile
import venv
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if sys.prefix == sys.base_prefix and (ROOT / '.translation-deps').exists():
    sys.path.insert(0, str(ROOT / '.translation-deps'))

from recipes import DB
from localization import TRANSLATIONS, initialize, translate_recipe

MODEL_URL = 'https://argos-net.com/v1/translate-en_ru-1_9.argosmodel'
MODEL_FILE = ROOT / 'data' / 'models' / 'translate-en_ru-1_9.argosmodel'

def validate_model(path):
    """Reject error pages, unfinished downloads and the reverse translation direction."""
    path = Path(path)
    if not path.is_file():
        raise ValueError(f'Model file not found: {path}')
    try:
        with zipfile.ZipFile(path) as archive:
            files = [x for x in archive.namelist() if Path(x).name == 'metadata.json']
            if len(files) != 1:
                raise ValueError('The model must contain one metadata.json.')
            metadata = json.loads(archive.read(files[0]))
            if metadata.get('from_code') != 'en' or metadata.get('to_code') != 'ru':
                raise ValueError('Choose the English-to-Russian (en -> ru) model.')
    except (zipfile.BadZipFile, json.JSONDecodeError) as error:
        raise ValueError('Invalid or incomplete .argosmodel file. Download the model again.') from error
    return path

def download_model(destination=MODEL_FILE):
    """Download the official model directly, without needing the GitHub index."""
    destination = Path(destination)
    if destination.exists():
        return validate_model(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix('.argosmodel.part')
    try:
        request = urllib.request.Request(MODEL_URL, headers={'User-Agent':'RecipeSearch/0.1'})
        with urllib.request.urlopen(request, timeout=30) as response, partial.open('wb') as handle:
            expected = int(response.headers.get('Content-Length', '0'))
            written = 0
            while chunk := response.read(1024 * 1024):
                handle.write(chunk)
                written += len(chunk)
                if written // (20 * 1024**2) != (written - len(chunk)) // (20 * 1024**2):
                    print(f'Model downloaded: {written / 1024**2:.0f} MiB', flush=True)
            if expected and expected != written:
                raise OSError('Incomplete model download.')
        validate_model(partial)
        partial.replace(destination)
        return destination
    except BaseException:
        partial.unlink(missing_ok=True)
        raise

def install_dependency():
    """Install and run in a virtual environment isolated from unrelated projects."""
    destination = ROOT / '.venv-translate'
    python = destination / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if not python.exists():
        venv.EnvBuilder(with_pip=True).create(destination)
    subprocess.run([str(python), '-m', 'pip', 'install', 'ctranslate2==4.9.0', 'sentencepiece==0.2.3',
                    '--retries', '1', '--timeout', '30'], check=True)
    arguments = [arg for arg in sys.argv[1:] if arg != '--install']
    return subprocess.call([str(python), str(Path(__file__).resolve()), *arguments])

def load_translator(setup=False, model=None):
    model = Path(model) if model else MODEL_FILE
    if not model.exists() and setup:
        print(f'Downloading English-to-Russian model: {MODEL_URL}', flush=True)
        download_model(model)
    model = validate_model(model)
    from tools.offline_translation import create_translator
    return create_translator(model, ROOT / 'data' / 'models' / 'runtime-en_ru')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--setup', action='store_true', help='Download and install en-to-ru model')
    parser.add_argument('--model', type=Path, help='Use local .argosmodel package without extra downloads')
    parser.add_argument('--install', action='store_true', help='Install CTranslate2 and SentencePiece in isolated .venv-translate')
    parser.add_argument('--export', type=Path, help='Export completed translations to CSV after this run')
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument('--limit', type=int, default=100, help='New recipes to translate (default: 100)')
    scope.add_argument('--all', action='store_true', help='Translate entire dataset; may take a long time')
    args = parser.parse_args()
    if args.limit < 1:
        parser.error('--limit must be positive')
    try:
        if not DB.exists():
            raise RuntimeError('Import recipes.csv first: python tools/dataset.py')
        if args.install:
            return install_dependency()
        translator = load_translator(args.setup, args.model)
        print('Checking translation model...', flush=True)
        probe = translator('Chicken soup.')
        if not probe:
            raise RuntimeError('Translation model did not return any text.')
        print(f'Model ready: {probe}', flush=True)
        initialize()
        count = 0
        started = time.monotonic()
        # Iterate source without holding a write lock on the translations database.
        with closing(sqlite3.connect(DB)) as con:
            con.row_factory = sqlite3.Row
            total = con.execute('SELECT count(*) FROM recipes').fetchone()[0]
            with closing(sqlite3.connect(TRANSLATIONS)) as progress:
                complete = progress.execute('SELECT count(*) FROM recipes').fetchone()[0]
            print(f'Recipes in database: {total}; already translated: {complete}', flush=True)
            for row in con.execute('SELECT id,name,category,ingredients,instructions FROM recipes ORDER BY id'):
                recipe = dict(row)
                for key in ('ingredients', 'instructions'):
                    recipe[key] = json.loads(recipe[key])
                if translate_recipe(recipe, translator):
                    count += 1
                    elapsed = time.monotonic() - started
                    print(f'Translated {count} this run: recipe {recipe["id"]}; '
                          f'{elapsed / count:.1f} seconds/recipe', flush=True)
                    if not args.all and count >= args.limit:
                        break
        print(f'Done: {count} new Russian translations. Refresh the app.', flush=True)
        if args.export:
            from tools.export_ru import export_csv
            print(export_csv(args.export))
        return 0
    except KeyboardInterrupt:
        print('Stopped. Completed recipes are saved; rerun the same command to resume.')
        return 130
    except Exception as error:
        print(f'Translation failed: {error}', file=sys.stderr)
        print('Completed recipes are saved. Rerun the same command after resolving the error.', file=sys.stderr)
        if not (args.model or MODEL_FILE).is_file():
            print(f'Model URL: {MODEL_URL}\nUse --model PATH to select a downloaded model.',file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
