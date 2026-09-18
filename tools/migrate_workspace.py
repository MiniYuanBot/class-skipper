"""One-time migration of the pre-workspace layout, preserving original receipts."""
import shutil
from pathlib import Path

from class_skipper.storage import read_json, write_json

root = Path(__file__).resolve().parents[1]
output, workspace = root / 'output', root / 'workspace'
for old, new in [('.runs', 'runs'), ('.cache', 'cache'), ('.locks', 'locks')]:
    source, target = output / old, workspace / new
    if source.exists():
        if target.exists():
            raise SystemExit(f'Refusing to merge existing {target}; inspect both directories.')
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(source, target)
for course in output.iterdir():
    if not course.is_dir():
        continue
    for receipt in course.glob('*/generated.json'):
        lecture = receipt.parent.name
        old = read_json(receipt)
        # Retain EXPECTED hashes, never approve a user's modified file as generated.
        files = {k: v for k, v in old.get('files', {}).items()
                 if k not in {'run.json', 'review.json', 'sources.json'}}
        write_json(workspace / 'published' / course.name / (lecture + '.json'), {'files': files})
        for name in ('generated.json', 'run.json', 'review.json', 'sources.json'):
            src = receipt.parent / name
            if src.exists():
                dst = workspace / 'legacy' / course.name / lecture / name
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(src, dst)
    for name in ('.backups', '.index.json', 'batch.json'):
        src = course / name
        if src.exists():
            dst = (workspace / 'published' / course.name / 'index.json' if name == '.index.json'
                   else workspace / 'legacy' / course.name / name)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(src, dst)
print('Legacy intermediates moved to workspace; final files preserved.')
