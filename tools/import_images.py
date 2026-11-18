"""Restore Food.com photo URLs from the downloaded CSV without reimporting recipes."""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from recipe_media import import_images

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv',type=Path)
    args = parser.parse_args()
    source = args.csv or next((p for p in [ROOT/'recipes.csv',ROOT/'data'/'recipes.csv'] if p.exists()),None)
    if not source:
        parser.error('Specify the Food.com CSV with --csv PATH.')
    print(import_images(source))

if __name__ == '__main__':
    main()
