#!/usr/bin/env python3
"""Use the verified complete Notes snapshot with an explicit local engine."""
import json
import argparse
import os
from pathlib import Path
import subprocess
import sys

from hsi_notes_domains import make_plan
from hsi_notes_review import PROTOCOL

ROOT = Path(__file__).resolve().parent


def verified_plan(root=ROOT):
    lock = json.loads((Path(root) / 'hsi_notes_review.lock.json').read_text(encoding='utf-8'))
    if lock.get('protocol') != PROTOCOL:
        raise ValueError('unsupported Notes lock')
    return make_plan(root, lock)


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in {'native', 'corpus', 'validate', 'plan', 'deploy'}:
        raise SystemExit('usage: hsi_notes_run.py native|corpus|validate|plan|deploy [args]')
    mode, args = sys.argv[1], sys.argv[2:]
    plan = verified_plan()
    print('notes_manifest>', plan['manifest_sha256'], flush=True)
    print('notes_sources>', plan['source_count'], flush=True)
    if mode == 'plan':
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return
    file = {'native': 'hsi_native_renderer.py', 'corpus': 'hsi_open_corpus.py',
            'validate': 'hsi_notes_validate.py', 'deploy': 'hsi_deploy.py'}[mode]
    env = os.environ.copy()
    if mode == 'native':
        # Keep engine CLI options intact; the first positional prompt contains
        # declared analogies plus exact identity of every reference document.
        prompt = plan['domain_plans']['music_native']['candidate_keywords'] + ' notes-manifest-' + plan['manifest_sha256']
        options = argparse.ArgumentParser(add_help=False)
        for option in ('--out', '--sr', '--bpm', '--bars'):
            options.add_argument(option)
        parsed, keywords = options.parse_known_args(args)
        flags = [part for name, value in vars(parsed).items() if value is not None for part in ('--' + name, value)]
        args = [*flags, prompt, *keywords]
    elif mode == 'corpus':
        args = ['--notes-root', str(ROOT), *args]
        env.setdefault('HSI_RC_MAX_CANDIDATES', '8')
    raise SystemExit(subprocess.call([sys.executable, str(ROOT / file), *args], env=env))


if __name__ == '__main__':
    main()
