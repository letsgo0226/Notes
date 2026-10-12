#!/usr/bin/env python3
"""Run bounded, offline Notes-to-audio and three-system invariant validations.

Only the pinned Native renderer, plaintext TM release, and exact common gate
snapshot execute. This runner has no network, broker, or deployment interface.
"""
import argparse
from array import array
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import wave

from hsi_notes_domains import canonical, make_plan, ReviewError
from hsi_notes_review import PROTOCOL as INVENTORY_PROTOCOL, git_blob_sha1

PROTOCOL = 'HSI-NOTES-LOCAL-VALIDATION/0.1'
RUNTIME_PROTOCOL = 'HSI-NOTES-LOCAL-RUNTIME-LOCK/0.1'
RELEASE = 'Notes/HSI_Prime_Analytic_2KB_Release'
ROOT = Path(__file__).resolve().parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n', encoding='utf-8')


def check_parameters(sr, bpm, bars):
    for value, low, high, name in ((sr, 8000, 48000, 'sr'), (bpm, 60, 180, 'bpm'), (bars, 4, 8, 'bars')):
        if type(value) is not int or not low <= value <= high:
            raise ReviewError(f'{name} must be an integer in {low}..{high}')


def verify_runtime(root, lock):
    if lock.get('protocol') != RUNTIME_PROTOCOL:
        raise ReviewError('unsupported runtime lock')
    required = {'native_renderer': 'hsi_native_renderer.py', 'three_system_core': 'validation_snapshots/hsi_three_system_core.py'}
    for key, rel in required.items():
        record = lock[key]
        path = root / rel
        if record.get('path') != rel or any(p.is_symlink() for p in [path, *path.parents]) or not path.is_file():
            raise ReviewError('missing or unsafe runtime: ' + rel)
        raw = path.read_bytes()
        if len(raw) != record['bytes'] or sha(raw) != record['sha256']:
            raise ReviewError('runtime differs from reviewed snapshot: ' + rel)
        if 'git_blob_sha1' in record and git_blob_sha1(raw) != record['git_blob_sha1']:
            raise ReviewError('runtime blob mismatch: ' + rel)


def clean_environment(**values):
    # Local HSI_CAND/HSI_STATE/HSI_LIMIT values must not leak into this run.
    env = {k: v for k, v in os.environ.items() if not k.startswith('HSI_')}
    env.update(values)
    return env


def execute(cmd, cwd, env=None, timeout=120):
    proc = subprocess.run(cmd, cwd=cwd, env=env or clean_environment(), capture_output=True, timeout=timeout)
    if proc.returncode:
        raise ReviewError(f'local validation failed (exit {proc.returncode}): ' + proc.stderr.decode('utf-8', 'replace')[-1500:])
    return proc.stdout


def d257(n):
    if type(n) is not int or n < 1:
        raise ReviewError('invalid E257 integer')
    digits = []
    while n > 1:
        n, remainder = divmod(n, 257)
        if not 1 <= remainder <= 256:
            raise ReviewError('invalid E257 digit')
        digits.append(remainder - 1)
    return bytes(reversed(digits))


def measure_wav(path, sr):
    with wave.open(str(path), 'rb') as audio:
        channels, width, rate, frames, compression, _ = audio.getparams()
        raw = audio.readframes(frames)
    if (channels, width, rate, compression) != (1, 2, sr, 'NONE') or not frames or len(raw) != frames * 2:
        raise ReviewError('WAV format or frame completeness failed')
    samples = array('h')
    samples.frombytes(raw)
    if sys.byteorder != 'little':
        samples.byteswap()
    rms = math.sqrt(sum(v * v for v in samples) / frames) / 32768
    peak = max(abs(v) for v in samples) / 32768
    clip = sum(abs(v) >= 32760 for v in samples) / frames
    silence = sum(abs(v) < 33 for v in samples) / frames
    if rms <= .0001 or clip > .0001 or silence >= .95:
        raise ReviewError('WAV is silent or clipped under declared technical thresholds')
    return {'channels': channels, 'sample_width_bytes': width, 'sample_rate': rate, 'frames': frames,
            'duration_seconds': frames / rate, 'rms': rms, 'peak': peak, 'clip_ratio': clip, 'silence_ratio': silence}


def render_native(root, stage, plan, sr, bpm, bars):
    prompt = plan['domain_plans']['music_native']['candidate_keywords'] + ' notes-manifest-' + plan['manifest_sha256']
    args = [sys.executable, '-I', str(root / 'hsi_native_renderer.py'), prompt, '--sr', str(sr), '--bpm', str(bpm), '--bars', str(bars)]
    output = stage / 'native'
    log = execute(args + ['--out', str(output)], stage)
    (stage / 'native-render.log').write_bytes(log)
    with tempfile.TemporaryDirectory(prefix='native-repeat-', dir=stage) as temporary:
        repeat = Path(temporary)
        execute(args + ['--out', str(repeat)], stage)
        identical = all((output / name).read_bytes() == (repeat / name).read_bytes() for name in ('song.wav', 'score.json', 'lyrics.txt'))
    if not identical:
        raise ReviewError('Native rerender bytes changed on the same runtime')
    raw = (output / 'song.wav').read_bytes()
    metrics = measure_wav(output / 'song.wav', sr)
    score = json.loads((output / 'score.json').read_text())
    expected_frames = int(score['bars'] * score['meter'] * 60 / score['bpm'] * sr)
    if score['bars'] != bars or score['bpm'] != bpm or abs(metrics['frames'] - expected_frames) > 1:
        raise ReviewError('score and actual WAV duration disagree')
    recovered = b''.join(d257(n) for n in json.loads((output / 'song.e257').read_text()))
    cert = json.loads((output / 'song.hsicert').read_text())
    if recovered != raw or cert.get('audio_sha256') != sha(raw):
        raise ReviewError('independent E257 reconstruction or audio digest failed')
    return {'status': 'LOCAL_AUDIO_VERIFIED', 'audio': 'native/song.wav', 'audio_sha256': sha(raw),
            'score_sha256': sha((output / 'score.json').read_bytes()), 'metrics': metrics,
            'same_runtime_rerender_identical': True, 'e257_reconstruction_verified': True,
            'conditioning': 'declared creative keywords plus fingerprint of all 16 files',
            'musical_quality_assessed': False, 'intelligible_singing_verified': False,
            'cross_platform_byte_identity_verified': False, 'remote_deployment': False}


def replay_utm(root, stage, plan):
    word = plan['domain_plans']['utm']['finite_word']
    if len(word) != 32 or any(c not in '01' for c in word):
        raise ReviewError('expected a 32-bit demonstration word')
    outputs, checkpoints = [], []
    for filename, label in (('OriginalXY_reference.py', 'reference'), ('HSI_OriginalXY_Plaintext_Core.py', '2kb-core')):
        state = stage / ('utm-' + label + '.state.json')
        env = clean_environment(HSI_WORD=word, HSI_LIMIT='32', HSI_BUDGET='8', HSI_SLEEP='0', HSI_TRACE='1', HSI_STATE=str(state))
        data = execute([sys.executable, '-I', str(root / RELEASE / filename)], stage, env, timeout=25)
        (stage / ('utm-' + label + '.jsonl')).write_bytes(data)
        outputs.append(data)
        checkpoints.append(state.read_bytes())
    if outputs[0] != outputs[1] or checkpoints[0] != checkpoints[1]:
        raise ReviewError('bounded TM replay differs between reference and 2KB core')
    rows = [json.loads(line) for line in outputs[0].splitlines()]
    finals = [row for row in rows if 'protocol' in row]
    if len(finals) != 32 or [r['step'] for r in finals] != list(range(32)):
        raise ReviewError('incomplete finite TM enumeration')
    traces = [row for row in rows if 'xy_step' in row]
    for row in traces:
        program, q, head, tape, candidate = json.loads(d257(int(row['x'])))
        successor = json.loads(d257(int(row['y'])))
        if successor != [program, *candidate] or row['accepted'] != 1:
            raise ReviewError('TM trace input/output binding failed')
        # Independent recomputation from the exact program and prior tape.
        w = (math.isqrt(8 * program + 1) - 1) // 2
        code = program - w * (w + 1) // 2
        halt_state = w - code + 1
        radix = 4 * (halt_state + 1)
        digit = (code // radix ** (2 * q + int(head in tape))) % radix
        next_q = digit % (halt_state + 1)
        digit //= halt_state + 1
        next_head = head + (1 if digit % 2 else -1)
        memory = set(tape)
        memory.add(head) if (digit // 2) % 2 else memory.discard(head)
        if candidate != [next_q, next_head, sorted(memory)]:
            raise ReviewError('independent TM transition recomputation failed')
    statuses = {s: sum(r['status'] == s for r in finals) for s in ('HALTED', 'UNRESOLVED', 'SKIPPED_BUDGET')}
    return {'status': 'BOUNDED_REPLAY_VERIFIED', 'enumeration_records': len(finals), 'verified_transitions': len(traces),
            'per_candidate_step_budget': 8, 'word': word, 'input_kind': 'manifest-digest-prefix-demo',
            'results': statuses, 'trace_sha256': sha(outputs[0]), 'checkpoint_sha256': sha(checkpoints[0]),
            'global_halting_decider': False, 'remote_deployment': False}


def check_domain_gates(root, stage, plan):
    # These are invariant certificates, not broker operations or Omega decisions.
    common = {'step': 1, 'previous_step': 0, 'branch': 0, 'budget': 32, 'subject_uid': plan['plan_uid'], 'claims': {}}
    requests = {
        'UTM': {**common, 'system': 'UTM', 'status': 'UNRESOLVED'},
        'TRADER_42': {**common, 'system': 'TRADER_42', 'status': 'HOLD', 'operation': 'HOLD', 'order': 0, 'from_state': 'FLAT', 'target_state': 'FLAT'},
        'OMEGA': {**common, 'system': 'OMEGA', 'status': 'HOLD'},
    }
    request_path = stage / 'gate-requests.json'
    write_json(request_path, requests)
    code = "import json,runpy,sys; gate=runpy.run_path(sys.argv[1]); requests=json.load(open(sys.argv[2])); r=requests[sys.argv[3]]; good=gate['certify'](r); bad=gate['certify']({**r,'claims':{'halting_decider':True}}); print(json.dumps({'request':r,'certificate':good,'forbidden_claim_certificate':bad}))"
    result = {}
    for system in requests:
        payload = execute([sys.executable, '-I', '-c', code, str(root / 'validation_snapshots/hsi_three_system_core.py'), str(request_path), system], stage,
                          clean_environment(HSI_SYSTEM=system, HSI_MAX_BUDGET='32', HSI_MAX_BODY='2048', HSI_GC='15'), timeout=25)
        record = json.loads(payload)
        good, bad = record['certificate'], record['forbidden_claim_certificate']
        if good['closed'] != 1 or good['role'] != system or good['subject_uid'] != plan['plan_uid'] or bad['closed'] != 0:
            raise ReviewError('common invariant gate failed for ' + system)
        write_json(stage / ('gate-' + system.lower() + '.json'), record)
        result[system] = {'status': 'LOCAL_INVARIANT_GATE_VERIFIED', 'positive_case_accepted': True,
                          'forbidden_claim_rejected': True, 'snapshot_only': True, 'broker_calls': 0,
                          'orders': 0, 'remote_deployment': False, 'ethical_truth_proven': False}
    return result


def verify_release(root, stage):
    # The upstream verifier rewrites its certificate. Copy it first so the locked
    # authoritative Notes inventory is never changed by validation.
    with tempfile.TemporaryDirectory(prefix='finite-release-', dir=stage) as temporary:
        copied = Path(temporary) / 'release'
        shutil.copytree(root / RELEASE, copied)
        log = execute([sys.executable, '-I', str(copied / 'verify_prime_analytic.py')], copied, timeout=120)
        (stage / 'finite-release.log').write_bytes(log)
        info = json.loads((copied / 'verification_certificate.json').read_text())
    if info.get('status') != 'FINITE_TESTS_PASSED':
        raise ReviewError('finite prime/analytic release check failed')
    write_json(stage / 'finite-release-certificate.json', info)
    return {'status': info['status'], 'replay_cases': len(info['bounded_semantic_replay']),
            'finite_interpolation_exact': info['analytic_continuation']['finite_lagrange_interpolation_exact'],
            'nonunique_interpolant_witness': info['analytic_continuation']['nonunique_entire_interpolant_witness']}


def run_validation(root, output, sr=24000, bpm=120, bars=4):
    check_parameters(sr, bpm, bars)
    root, output = Path(root).resolve(), Path(output).expanduser().absolute()
    lock = json.loads((root / 'hsi_notes_review.lock.json').read_text())
    if lock.get('protocol') != INVENTORY_PROTOCOL:
        raise ReviewError('unsupported Notes inventory lock')
    plan = make_plan(root, lock)
    runtime = json.loads((root / 'hsi_notes_runtime.lock.json').read_text())
    verify_runtime(root, runtime)
    if output.exists() or output.is_symlink() or (root / 'Notes') in output.resolve().parents:
        raise ReviewError('output must be a new directory outside the locked Notes tree')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='hsi-local-validation-', dir=output.parent) as temporary:
        stage = Path(temporary) / 'result'
        stage.mkdir()
        write_json(stage / 'domain-plan.json', plan)
        native = render_native(root, stage, plan, sr, bpm, bars)
        utm = replay_utm(root, stage, plan)
        gates = check_domain_gates(root, stage, plan)
        finite = verify_release(root, stage)
        if make_plan(root, lock) != plan:
            raise ReviewError('Notes sources changed during validation')
        verify_runtime(root, runtime)
        result = {
            'protocol': PROTOCOL, 'status': 'LOCAL_VALIDATION_PASSED_NOT_DEPLOYED',
            'source_count': plan['source_count'], 'source_commit': plan['source_commit'],
            'manifest_sha256': plan['manifest_sha256'], 'plan_uid': plan['plan_uid'],
            'runtime_sources': runtime, 'parameters': {'sample_rate': sr, 'bpm': bpm, 'bars': bars},
            'domain_results': {'music_native': native, 'utm': utm,
                'trader_42': {**gates['TRADER_42'], 'mode': 'HOLD_CERTIFICATE_ONLY'},
                'omega': {**gates['OMEGA'], 'human_normative_review': 'PENDING'},
                'music_corpus': {'status': 'NOT_EXECUTED', 'external_search_performed': False, 'rights_verified': False},
                'music_ai_bridge': {'status': 'NOT_EXECUTED', 'paid_api_calls': 0}},
            'common_gate_results': gates, 'finite_release': finite,
            'claims': {'remote_deployment': False, 'live_trading': False, 'paid_api_calls': 0,
                       'mathematical_or_ethical_truth_proven': False},
        }
        write_json(stage / 'validation-certificate.json', result)
        # The Native manifest embeds its staging directory; make the delivered
        # path accurate without changing any audio/score/certificate bytes.
        manifest_path = stage / 'native/manifest.json'
        manifest = json.loads(manifest_path.read_text())
        manifest['output'] = str(output / 'native')
        write_json(manifest_path, manifest)
        stage.rename(output)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default=str(ROOT))
    parser.add_argument('--out', default=str(Path.home() / 'Music/HSI-Notes' / (time.strftime('%Y%m%d-%H%M%S') + '-' + str(os.getpid()))))
    parser.add_argument('--sr', type=int, default=24000)
    parser.add_argument('--bpm', type=int, default=120)
    parser.add_argument('--bars', type=int, default=4)
    args = parser.parse_args()
    try:
        result = run_validation(args.root, args.out, args.sr, args.bpm, args.bars)
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired, wave.Error) as exc:
        parser.exit(2, 'LOCAL_VALIDATION_FAILED: ' + str(exc) + '\n')
    print(json.dumps({'status': result['status'], 'source_count': result['source_count'],
                      'audio': str(Path(args.out).expanduser().absolute() / 'native/song.wav'),
                      'certificate': str(Path(args.out).expanduser().absolute() / 'validation-certificate.json')}, ensure_ascii=False))


if __name__ == '__main__':
    raise SystemExit(main())
