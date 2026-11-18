"""Apply authored Russian translations without installing a translation model."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from recipes import detail
from localization import initialize, translate_recipe

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--file', type=Path, default=ROOT / 'data' / 'manual_ru.json')
    args = parser.parse_args()
    entries = json.loads(args.file.read_text(encoding='utf-8'))
    prepared = []
    # Validate the complete batch before changing any stored translation.
    for entry in entries:
        source = detail(entry['id'], language='en')
        if not source or source['name'] != entry['source_name']:
            raise ValueError(f'Source recipe mismatch: {entry["id"]}')
        mapping = {source['name']:entry['name'], source['category']:entry['category']}
        for key in ('ingredients', 'instructions'):
            if len(source[key]) != len(entry[key]):
                raise ValueError(f'Element count mismatch: {entry["id"]} {key}')
            for original, translated in zip(source[key], entry[key]):
                if not isinstance(translated, str) or not translated.strip():
                    raise ValueError(f'Empty translation: {entry["id"]} {key}')
                if original in mapping and mapping[original] != translated:
                    raise ValueError(f'Conflicting translation: {entry["id"]}')
                mapping[original] = translated
        prepared.append((source, mapping))
    initialize()
    count = 0
    for source, mapping in prepared:
        count += translate_recipe(source, mapping.__getitem__, method='manual', overwrite=True,
                                  use_cache=False)
    print(f'Applied {count} manual translations.')

if __name__ == '__main__':
    main()
