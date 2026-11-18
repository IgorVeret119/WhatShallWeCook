"""Download the real Food.com CSV, or import a previously downloaded copy."""
import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from recipes import DOWNLOAD, ROOT, import_csv
from recipe_media import import_images

def download(target):
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix('.csv.part')
    request = urllib.request.Request(DOWNLOAD, headers={'User-Agent': 'RecipeSearch/0.1'})
    digest = hashlib.sha256()
    written = 0
    try:
        with urllib.request.urlopen(request, timeout=60) as response, partial.open('wb') as out:
            expected = int(response.headers.get('Content-Length', '0'))
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
                digest.update(chunk)
                written += len(chunk)
                if written // (20 * 1024 * 1024) != (written - len(chunk)) // (20 * 1024 * 1024):
                    print(f'Downloaded {written / 1024**2:.0f} MiB', flush=True)
            if expected and written != expected:
                raise OSError('Incomplete download')
        # Detect HTML error pages before replacing a valid download.
        with partial.open(encoding='utf-8-sig') as handle:
            if 'RecipeId' not in handle.readline():
                raise ValueError('The server did not return a Food.com CSV.')
        partial.replace(target)
        manifest = {'url': DOWNLOAD, 'bytes': written, 'sha256': digest.hexdigest()}
        target.with_suffix('.source.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    except BaseException:
        partial.unlink(missing_ok=True)
        raise

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', type=Path, help='Import existing Food.com Recipes and Reviews CSV')
    args = parser.parse_args()
    target = args.csv or ROOT / 'data' / 'recipes.csv'
    if not args.csv and not target.exists() and (ROOT / 'recipes.csv').exists():
        target = ROOT / 'recipes.csv'
    try:
        if not args.csv and not target.exists():
            print('Downloading Food.com CSV (~704 MB). No images or reviews.', flush=True)
            download(target)
        print(import_csv(target))
        print(import_images(target))
        return 0
    except (OSError, ValueError) as error:
        print(f'Dataset not imported: {error}\n'
              'Download recipes.csv manually and run: python tools/dataset.py --csv PATH', file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
