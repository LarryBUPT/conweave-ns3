#!/usr/bin/env python3
"""Prepare a reviewable test-only compatibility contract; never contact SSH."""
import difflib
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = '526802e6b25635435aba960d821e8e5561ebb50a'
NAME = 'src/core/test/command-line-test-suite.cc'
ATTEMPT = '20261022-173000-ws29-eng-unit-compat-r1'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-sha', default=SOURCE)
    parser.add_argument('--output', type=Path, default=ROOT / 'docs/research/evidence/ws29-unit-compat-contract.json')
    args = parser.parse_args()
    original = subprocess.check_output(['git', 'show', args.source_sha + ':' + NAME], cwd=ROOT)
    if hashlib.sha256(original).hexdigest() != 'b7285686202442d47d339fd5817e9001c47bfc23377c8a8f5f596ba694373881':
        raise ValueError('Core original hash changed')
    token = b'Parse (const CommandLine &cmd, int n, ...)'
    if original.count(token) != 2:
        raise ValueError('Expected exactly the declaration and definition')
    patched = original.replace(token, b'Parse (CommandLine &cmd, int n, ...)')
    diff = ''.join(difflib.unified_diff(original.decode().splitlines(True),
                                      patched.decode().splitlines(True),
                                      fromfile='a/' + NAME, tofile='b/' + NAME))
    data = {'kind': 'test-only compatibility contract; remote GO pending',
            'source_sha': args.source_sha, 'previous_source_sha': SOURCE,
            'failed_id': '20261022-150000-ws29-eng-unit',
            'new_id': ATTEMPT, 'remote_id_availability': 'not checked; SSH forbidden in this stage',
            'file': NAME, 'original_sha256': hashlib.sha256(original).hexdigest(),
            'patched_sha256': hashlib.sha256(patched).hexdigest(), 'exact_diff': diff,
            'scope': 'Only the new isolated test source copy. No routing, transport, scoring or demand changes.',
            'steps': [
                'Refuse existing run/result ID; clone and checkout exact source SHA into the new ID.',
                'Verify HEAD and clean tracked source; hash the original file and archive its bytes and exact diff in result logs.',
                'Complete the unmodified optimized build before applying the compatibility patch.',
                'Apply only the two exact replacements after original hash validation.',
                './waf configure --enable-tests --build-profile=optimized --out=build-ws29-tests',
                './waf --out=build-ws29-tests -j2',
                'Record suite listing and run optimized test runner with --suite=devices-point-to-point --verbose and isolated LD_LIBRARY_PATH.',
                'In finally, restore archived original bytes even on failure; verify original SHA256 and clean tracked git diff.',
                'Archive patched hash, exact diff, original/restored hashes, commands, return codes and complete resource receipts.',
                'Keep original failed ID unchanged. Do not start any simulation.'],
            'interpretation': 'PASS applies to an optimized test-enabled binary compiled with the disclosed two-line compatibility edit. Restoring source does not undo the compiled binary edit. Formal simulation copies must be fresh, unpatched checkouts.',
            'acceptance': ['All intended suite cases PASS, including v2/v3 and boundary tests.',
                           'Original and restored hashes equal; patched hash equals the contract.',
                           'No tracked differences except the disclosed edit while compiling tests.',
                           'Nonempty resource samples and terminal TESTED receipt; no automatic retry.']}
    target = args.output
    encoded = json.dumps(data, ensure_ascii=False, indent=2) + '\n'
    if target.exists() and target.read_text(encoding='utf-8') != encoded:
        raise ValueError('Refuse changed contract overwrite')
    target.write_text(encoded, encoding='utf-8')
    target.with_suffix('.patch').write_text(diff, encoding='utf-8', newline='\n')
    print(json.dumps({k: data[k] for k in ('new_id', 'source_sha', 'original_sha256', 'patched_sha256')}))


if __name__ == '__main__':
    main()
