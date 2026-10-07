"""Commit an explicitly reviewed registry patch. No chart inference or TV writes."""
import argparse
import copy
import json
from datetime import date, datetime, timezone
from pathlib import Path
from research_store import atomic_json, immutable_json, timestamp, research_day
from setup_journey import validate_review_transition, entry_plan, reviewed_origin
from setup_lifecycle import load_registry_for_date, VALID_SETUP_TYPES, VALID_LIFECYCLES

ROOT = Path(__file__).resolve().parents[1]


def save_review(doc, root=ROOT):
    asof = doc['asOf']
    date.fromisoformat(asof)
    if timestamp(doc['reviewedAt'])>datetime.now(timezone.utc):
        raise ValueError('Chart review timestamp cannot be in the future')
    if research_day(doc['reviewedAt']) != asof or not doc.get('reviewer') or not doc.get('changeReason'):
        raise ValueError('Review date, zoned time, reviewer and change reason are required')
    patches = doc.get('symbols', {})
    if not patches:
        raise ValueError('No submitted chart reviews')
    directory = root/'data/setup-state/registry'
    manifest_path = directory/'manifest.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {'schemaVersion':1,'entries':[]}
    if any(e['asOf'] > asof for e in manifest['entries']):
        raise ValueError('Cannot insert a past review behind an existing registry')
    latest = load_registry_for_date(root, asof)
    symbols = copy.deepcopy(latest['symbols'])
    for symbol, proposed in patches.items():
        if not symbol.startswith(('NASDAQ:','NYSE:','AMEX:','TSE:')):
            raise ValueError('Unsupported research symbol')
        if proposed.get('market') != ('JP' if symbol.startswith('TSE:') else 'US'):
            raise ValueError('Symbol/market mismatch')
        if proposed.get('setup_type') not in VALID_SETUP_TYPES or proposed.get('lifecycle') not in VALID_LIFECYCLES:
            raise ValueError('Unsupported setup type/lifecycle')
        validate_review_transition(symbols.get(symbol), proposed, asof)
        review = reviewed_origin(proposed, asof, asof)
        plan = entry_plan(proposed, review, proposed['lifecycle'], True, asof)
        if any(p['status'] == 'INVALID' for p in plan['alternatives']):
            raise ValueError('Invalid entry plan; fix its Pivot/Stop before saving')
        symbols[symbol] = copy.deepcopy(proposed)
    saved = {'schemaVersion':1,'asOf':asof,'reviewedAt':doc['reviewedAt'],'reviewer':doc['reviewer'],
             'changeReason':doc['changeReason'],'source':'EXPLICIT_CHART_REVIEW','symbols':symbols}
    path = directory/f'{asof}.json'
    # Validate everything first. A failed save never advances the manifest.
    immutable_json(path, saved)
    item = {'asOf':asof,'path':f'setup-state/registry/{asof}.json'}
    entries = {e['asOf']:e for e in manifest['entries']}
    entries[asof] = item
    atomic_json(manifest_path, {**manifest, 'entries':[entries[k] for k in sorted(entries)]})
    return {'asOf':asof,'reviewedSymbols':len(patches),'saved':True,'watchlistsChanged':False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(save_review(json.loads(args.input.read_text()))))
