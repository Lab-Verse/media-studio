"""Offline public-snapshot syntax, source-integrity, links and disclosure checks."""
import ast
import hashlib
import json
from pathlib import Path
import re
import sys
import tomllib
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
SKIP = {'.git', '__pycache__', '.venv', 'cache', 'output', 'models'}


def main():
    errors = []
    counts = {'python': 0, 'json': 0, 'toml': 0, 'links': 0}
    for path in sorted(ROOT.rglob('*')):
        relative = path.relative_to(ROOT)
        if not path.is_file() or any(p in SKIP for p in relative.parts):
            continue
        try:
            text = path.read_text(encoding='utf-8-sig')
            if path.suffix == '.py':
                ast.parse(text, filename=str(relative)); counts['python'] += 1
            elif path.suffix == '.json':
                json.loads(text); counts['json'] += 1
            elif path.suffix == '.toml':
                tomllib.loads(text); counts['toml'] += 1
            if path.suffix == '.md':
                for target in re.findall(r'\]\(([^)]+)\)', text):
                    if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target) or target.startswith('#'):
                        continue
                    target = unquote(target.split('#')[0].strip('<>'))
                    if not target or '<' in target or '>' in target:
                        continue
                    counts['links'] += 1
                    if not (path.parent / target).exists():
                        errors.append(f'{relative}: missing local link {target}')
            # Report only paths and categories, never candidate secret values.
            for label, pattern in [
                ('private key', r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
                ('GitHub token', r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b'),
                ('Google client secret', r'GOCSPX-[A-Za-z0-9_-]{20,}'),
                ('workstation identity', r'[A-Za-z]:[\\/]Users[\\/][A-Za-z0-9]'),
                ('private host address', r'\b(?:192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+)\b'),
            ]:
                if re.search(pattern, text):
                    errors.append(f'{relative}: possible {label}')
        except (SyntaxError, ValueError, UnicodeError) as error:
            errors.append(f'{relative}: {type(error).__name__}: {error}')
    smoke = json.loads((ROOT / 'runtime/documentary_engine/projects/smoke/manifest.json').read_text())
    scenes = [s for c in smoke['chapters'] for s in c['scenes']]
    if len(scenes) != 2 or any(s.get('timestamp_overlay') and s['visual'].get('motion', 'none') == 'none' for s in scenes):
        errors.append('Smoke fixture must exercise two moving, timestamped scenes')
    if scenes[0]['visual'].get('type') == 'ai_cinematic' or not scenes[0]['visual'].get('query') or scenes[1]['visual'].get('type') != 'ai_cinematic':
        errors.append('Live smoke directions must preserve the stock-first / independent-AI contract')
    manifest = json.loads((ROOT / 'docs/SOURCE-MANIFEST.json').read_text())
    for entry in manifest['records']:
        path = ROOT / entry['path']
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry['published_sha256']:
            errors.append(f"{entry['path']}: published source hash differs")
    if errors:
        print('\n'.join(errors)); return 1
    print('Passed offline syntax, local-link, source-hash and high-confidence disclosure checks:', counts)
    return 0


if __name__ == '__main__':
    sys.exit(main())
