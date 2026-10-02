"""Manual, conservative refresh. Never imported by application startup.

Fetches verify the committed facts before updating retrieval dates. Changed facts
require a reviewed --import-dir JSON snapshot, rather than guessing from markup.
"""
import argparse
import csv
import io
import json
import re
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.request import urlopen

DATA = Path(__file__).resolve().parents[1] / 'data'


def validate_snapshot(candidate, previous):
    for key in ('source_id', 'title', 'publisher', 'url', 'source_type', 'facts_used', 'notes'):
        if not candidate.get(key):
            raise ValueError(f'Missing {key}')
    if candidate['source_id'] != previous['source_id'] or candidate['url'] != previous['url']:
        raise ValueError('Source identity changed')
    for key, value in previous['facts_used'].items():
        new = candidate['facts_used'].get(key)
        if type(new) is not type(value) or (isinstance(new, (int, float)) and new <= 0):
            raise ValueError(f'Invalid expected fact: {key}')


def page_text(raw):
    # Help articles keep their actual content in Next.js JSON, not visible HTML.
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', raw, re.S)
    if match:
        article = json.loads(match.group(1))['props']['pageProps'].get('article')
        if article:
            raw = json.dumps(article)
    return unescape(re.sub(r'<[^>]+>', ' ', raw)).replace('\\n', ' ')


def verify_facts(text, source):
    facts = source['facts_used']
    # Conservative detection: if a site's format or fact changes, retain prior snapshot.
    tokens = {
        'teleport_1h_2026': ['156.4', '12.1', '182,660', '118.2', '290', '80', '7%', '89%', *facts.get('partner_names', [])],
        'teleport_network_2026': ['A321F', '3', '17', '55+', '640+', '200+', '730+'],
        'teleport_routes_2022': facts.get('destinations', []),
        'teleport_fsc_reference': ['90', 'weekly', 'USD', 'kg', 'Platts', 'IATA'],
        'iata_fuel_2026': ['152', '31.4', '90'],
    }[source['source_id']]
    compact = re.sub(r'\s+', '', text).lower()
    for token in tokens:
        if re.sub(r'\s+', '', str(token)).lower() not in compact:
            raise ValueError(f'Cannot verify expected fact {token}; review source manually')


def atomic_json(path, value):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, indent=2) + '\n')
    temp.replace(path)


def refresh(fetch=False, import_dir=None):
    registry_path = DATA / 'provenance/source_registry.json'
    registry = json.loads(registry_path.read_text())
    failures = 0
    for index, entry in enumerate(registry):
        path = DATA / 'sources' / entry['snapshot']
        try:
            if entry['source_type'] == 'OPEN_DATA':
                rows = list(csv.DictReader(path.open()))
                if fetch:
                    with urlopen(entry['download_url'], timeout=30) as response:
                        incoming = list(csv.DictReader(io.StringIO(response.read().decode('utf-8'))))
                    codes = {r['iata_code'] for r in rows}
                    rows = [{k: r.get('ident' if k == 'icao_code' else k, '') for k in rows[0]} for r in incoming if r['iata_code'] in codes and r['type'] == 'large_airport']
                    if {r['iata_code'] for r in rows} != codes or len(rows) != len(codes):
                        raise ValueError('Airport coverage mismatch')
                for row in rows:
                    if not row['name'] or not row['iso_country'] or not -90 <= float(row['latitude_deg']) <= 90 or not -180 <= float(row['longitude_deg']) <= 180:
                        raise ValueError('Invalid airport metadata')
                if fetch:
                    temp = path.with_suffix('.tmp')
                    with temp.open('w', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=rows[0], lineterminator="\n"); writer.writeheader(); writer.writerows(sorted(rows, key=lambda r: r['iata_code']))
                    temp.replace(path)
                    registry[index] = {**entry, 'retrieved_at': datetime.now(timezone.utc).isoformat()}
            else:
                previous = json.loads(path.read_text())
                candidate = json.loads((import_dir / path.name).read_text()) if import_dir else dict(previous)
                validate_snapshot(candidate, previous)
                if fetch:
                    urls = [entry['url'], *entry.get('supporting_urls', [])]
                    texts = []
                    for url in urls:
                        with urlopen(url, timeout=30) as response:
                            texts.append(page_text(response.read().decode('utf-8')))
                    verify_facts(' '.join(texts), candidate)
                if fetch or import_dir:
                    candidate['retrieved_at'] = datetime.now(timezone.utc).isoformat()
                    atomic_json(path, candidate)
                    registry[index] = candidate
            print(f'OK {entry["source_id"]}: {"updated" if fetch or import_dir else "validated local snapshot"}')
        except Exception as exc:
            failures += 1
            print(f'RETAINED {entry["source_id"]}: {exc}; previous valid snapshot preserved')
    if fetch or import_dir:
        atomic_json(registry_path, registry)
    print(f'{len(registry) - failures}/{len(registry)} sources validated; {failures} retained after failure. Startup remains offline.')
    return failures


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch', action='store_true')
    parser.add_argument('--import-dir', type=Path, help='Reviewed JSON snapshots; no automatic guessing of changed public facts')
    args = parser.parse_args()
    raise SystemExit(bool(refresh(args.fetch, args.import_dir)))
