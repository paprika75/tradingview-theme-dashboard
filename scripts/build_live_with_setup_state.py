"""Canonical observed build with point-in-time setup state enrichment.

The existing technical builder remains the calculation core. This wrapper injects setup_type,
lifecycle and lifecycleCandidate immediately before immutable snapshot writes, so reruns remain
idempotent and historical registry state is never backfilled from the future.
"""
import argparse
import json
from pathlib import Path
from datetime import datetime

import build_live as core
from setup_lifecycle import apply_setup_state, load_registry_for_date
from setup_journey import build_journey, load_pre_setup, reviewed_origin

VERSION = '3.3.0-setup-journey-v1'


def enrich_quantitative(q, bars, state, rules, registry_asof, target):
    state = state or {}
    review = reviewed_origin(state, registry_asof, target)
    # Candidate rules use the confirmed origin Pivot when available. Legacy
    # scalar levels stay untouched and are not continuation entry plans.
    candidate_input = dict(q)
    if review:
        candidate_input['entry'] = review['originPivot']['price']
    apply_setup_state(candidate_input, bars, state, rules, registry_asof)
    for key in ['setup_type','setupConfirmed','setupTypeSource','setupRegistryAsOf',
                'lifecycle','lifecycleConfirmed','lifecycleSource','lifecycleCandidate',
                'lifecycleCandidateReasons','lifecycleRuleVersion','setup']:
        q[key] = candidate_input.get(key)
    q['lifecycleCandidatePivot'] = review['originPivot'] if review else None
    return q


def collect_bars(bundle):
    fetched = datetime.fromisoformat(bundle['fetchedAt'].replace('Z', '+00:00'))
    allbars = {}
    for symbol, doc in bundle['documents'].items():
        market = 'JP' if symbol.startswith(('TSE:', 'TVC:NI225')) else 'US'
        try:
            allbars[symbol] = core.valid_bars(doc, market, fetched, symbol)
        except ValueError:
            allbars[symbol] = []
    return allbars


def enrich_snapshot(data, allbars, rules, root=core.ROOT):
    if not isinstance(data, dict) or 'markets' not in data or 'asOf' not in data:
        return data
    target = data['asOf']
    registry = load_registry_for_date(root, target)
    symbols = registry.get('symbols', {})
    pre_doc = load_pre_setup(root, target)
    markets = data.get('markets', {})
    touched = 0
    for market, market_data in markets.items():
        pre_rows = {r['symbol']: r for r in (pre_doc or {}).get('markets', {}).get(market, {}).get('stocks', [])}
        journeys = {}
        for theme in market_data.get('themes', []):
            setup_count = 0
            for stock in theme.get('stocks', []):
                symbol = stock.get('symbol')
                q = stock.get('quantitative') or {}
                bars = [b for b in allbars.get(symbol, []) if b['date'] <= target]
                enrich_quantitative(q, bars, symbols.get(symbol), rules, registry.get('asOf'), target)
                journey = build_journey(symbol, q, symbols.get(symbol) or {}, registry.get('asOf'),
                                        pre_rows.get(symbol), pre_doc, target)
                q['setupJourney'] = journey
                if journey['phase'] != 'UNASSESSED' or q.get('setup_type') or symbol in symbols:
                    journeys[symbol] = journey
                stock['quantitative'] = q
                if q.get('setup_type') or q.get('setup'):
                    setup_count += 1
                touched += 1
            if isinstance(theme.get('quantitative'), dict):
                theme['quantitative']['setupCount'] = setup_count
        # Primary-screener candidates can be outside the current theme catalogue.
        extra_symbols = set(pre_rows) | {s for s, v in symbols.items() if v.get('market') == market}
        for symbol in sorted(extra_symbols):
            row = pre_rows.get(symbol)
            if symbol not in journeys:
                state = symbols.get(symbol) or {}
                bars = [b for b in allbars.get(symbol, []) if b['date'] <= target]
                benchmark = [{**b, 'market': market} for b in allbars.get('SP:SPX' if market == 'US' else 'TVC:NI225', [])]
                q = core.metrics(bars, benchmark, target) if bars and benchmark else {'price': None}
                enrich_quantitative(q, bars, state, rules, registry.get('asOf'), target)
                journeys[symbol] = build_journey(symbol, q, state, registry.get('asOf'), row, pre_doc, target)
        market_data['setupJourneys'] = list(journeys.values())
        market_data['setupStateMeta'] = {
            'registryAsOf': registry.get('asOf'),
            'registrySource': registry.get('source'),
            'lifecycleRuleVersion': rules.get('version'),
            'journeyModelVersion': '1.0.0',
            'preSetupAsOf': (pre_doc or {}).get('asOf'),
            'policy': 'manual registry wins; automated lifecycleCandidate requires chart review'
        }
    data['setupState'] = {
        'schemaVersion': 1,
        'registryAsOf': registry.get('asOf'),
        'lifecycleRuleVersion': rules.get('version'),
        'enrichedStocks': touched,
        'policy': 'manual registry wins; no future registry state is joined to historical snapshots'
    }
    return data


def build(input_path, activate=False):
    input_path = Path(input_path)
    bundle = json.loads(input_path.read_text())
    allbars = collect_bars(bundle)
    config = json.loads((core.ROOT / 'config/versions' / f'{VERSION}.json').read_text())
    rules = config['setupLifecycle']
    original_version = core.VERSION
    original_immutable = core.immutable

    def immutable_with_setup_state(path, data):
        # Only the full daily/weekly market snapshot contains themes/stocks. Raw files pass through.
        if isinstance(data, dict) and data.get('markets') and data.get('period') in {'daily', 'weekly'}:
            enrich_snapshot(data, allbars, rules)
        original_immutable(path, data)

    core.VERSION = VERSION
    core.immutable = immutable_with_setup_state
    try:
        return core.build(input_path, activate)
    finally:
        core.VERSION = original_version
        core.immutable = original_immutable


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--activate', action='store_true')
    args = parser.parse_args()
    build(args.input, args.activate)
