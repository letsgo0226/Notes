#!/usr/bin/env python3
"""Install one immutable, hash-verified Notes runtime bundle, then launch it."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request

REPO = 'letsgo0226/Notes'
MAX_BYTES = 4 * 1024 * 1024


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'HSI-NOTES-BOOTSTRAP/1.0'})
    with urllib.request.urlopen(req, timeout=30) as response:
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError('bundle file exceeds byte budget')
    return raw


def install(root, ref):
    root = Path(root).expanduser()
    if re.fullmatch('[0-9a-f]{40}', ref):
        commit = ref
    else:
        meta = json.loads(fetch('https://api.github.com/repos/' + REPO + '/commits/' + urllib.parse.quote(ref, safe='')))
        commit = meta['sha']
    if not re.fullmatch('[0-9a-f]{40}', commit):
        raise ValueError('invalid source commit')
    base = 'https://raw.githubusercontent.com/' + REPO + '/' + commit + '/'
    lock_raw = fetch(base + 'hsi_bundle.lock.json')
    lock = json.loads(lock_raw)
    if lock.get('protocol') != 'HSI-NOTES-BUNDLE/1.0' or not 12 <= len(lock.get('files', [])) <= 64:
        raise ValueError('invalid bundle lock')
    seen = set()
    for row in lock['files']:
        p = Path(row['path'])
        if p.is_absolute() or '..' in p.parts or '\\' in row['path'] or row['path'] != p.as_posix() or row['path'] in seen:
            raise ValueError('unsafe bundle path')
        seen.add(row['path'])
        if not re.fullmatch('[0-9a-f]{64}', row['sha256']):
            raise ValueError('invalid bundle digest')
    releases = root / 'releases'
    releases.mkdir(parents=True, exist_ok=True)
    final = releases / commit
    def matches(directory):
        return directory.is_dir() and not directory.is_symlink() and (directory / 'hsi_bundle.lock.json').read_bytes() == lock_raw and all(
            (directory / row['path']).is_file() and not (directory / row['path']).is_symlink()
            and hashlib.sha256((directory / row['path']).read_bytes()).hexdigest() == row['sha256'] for row in lock['files'])
    if final.exists():
        if not matches(final):
            raise ValueError('cached bundle differs from immutable lock; use a new HSI_BUNDLE_HOME')
    else:
        with tempfile.TemporaryDirectory(prefix='bundle-', dir=releases) as temporary:
            stage = Path(temporary) / 'payload'
            stage.mkdir()
            def download(row):
                raw = fetch(base + urllib.parse.quote(row['path'], safe='/'))
                if hashlib.sha256(raw).hexdigest() != row['sha256'] or len(raw) != row['bytes']:
                    raise ValueError('bundle verification failed: ' + row['path'])
                output = stage / row['path']
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(raw)
            with ThreadPoolExecutor(max_workers=4) as workers:
                list(workers.map(download, lock['files']))
            (stage / 'hsi_bundle.lock.json').write_bytes(lock_raw)
            subprocess.run([sys.executable, str(stage / 'hsi_notes_review.py'), '--root', str(stage)], check=True, stdout=subprocess.DEVNULL)
            stage.rename(final)
    print('bundle_commit>', commit, flush=True)
    return final


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('engine', choices=['corpus', 'native', 'validate', 'plan', 'deploy'])
    parser.add_argument('args', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if sys.version_info < (3, 9):
        parser.exit(2, 'Python 3.9+ required\n')
    try:
        directory = install(os.getenv('HSI_BUNDLE_HOME', str(Path.home() / '.hsi-notes')), os.getenv('HSI_BUNDLE_REF', 'main'))
    except Exception as exc:
        parser.exit(2, 'BUNDLE_FAILED: ' + str(exc) + '\n')
    # Windows exec emulation lets the launcher exit before the spawned program;
    # wait for the actual render so completion means files are ready.
    raise SystemExit(subprocess.call([sys.executable, str(directory / 'hsi_notes_run.py'), args.engine, *args.args]))


if __name__ == '__main__':
    main()
