#!/usr/bin/env python3
"""Package only the extension, excluding generated Python caches."""
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def main():
    root = Path(__file__).resolve().parents[1]
    extension = root / 'DECKTOOLS.extension'
    destination = root / 'dist' / 'DECKTOOLS.extension.zip'
    destination.parent.mkdir(exist_ok=True)
    with ZipFile(destination, 'w', ZIP_DEFLATED) as archive:
        for path in sorted(extension.rglob('*')):
            if (path.is_file() and '__pycache__' not in path.parts
                    and path.suffix not in ('.pyc', '.pyo')):
                archive.write(path, path.relative_to(root))
    print(destination)


if __name__ == '__main__':
    main()
