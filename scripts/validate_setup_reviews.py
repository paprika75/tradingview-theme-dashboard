"""Validate a proposed dated registry; never save it or change watchlists."""
import argparse
import json
from pathlib import Path
from setup_journey import validate_review_transition
from setup_lifecycle import load_registry_for_date

ROOT = Path(__file__).resolve().parents[1]

def validate(doc, root=ROOT):
    asof = doc['asOf']
    previous = load_registry_for_date(root, asof).get('symbols', {})
    count = 0
    for symbol, state in doc.get('symbols', {}).items():
        if state.get('setupReview'):
            validate_review_transition(previous.get(symbol), state, asof)
            count += 1
    return {'asOf': asof, 'reviewedSymbols': count, 'saved': False, 'watchlistsChanged': False}

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(validate(json.loads(args.input.read_text()))))
