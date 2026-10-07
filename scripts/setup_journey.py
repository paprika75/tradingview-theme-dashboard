"""Read-only promotion and entry-plan model; never writes TradingView state.

All adoption requires dated chart-review records. Legacy scalar entry/stop values
and automatic lifecycle candidates are deliberately not used as reviewed plans.
"""
import json
from datetime import date
from pathlib import Path

from setup_lifecycle import VALID_SETUP_TYPES, POST_BREAKOUT, finite

MODEL_VERSION = '1.0.0'
ENTRY_KINDS = {
    'SETUP': ['STANDARD', 'EARLY', 'CHEAT'],
    'BREAKOUT': ['BREAKOUT'],
    'EXTENDED': [],
    'PULLBACK': ['CONTINUATION'],
    'RETEST': ['REENTRY'],
    '3WT': ['ADD_ON', 'CONTINUATION'],
    'TIGHT': ['ADD_ON', 'CONTINUATION'],
    'ASCENDING_BASE': ['NEW_PIVOT'],
    'FAILED_BREAKOUT': [],
    'UNASSESSED': [],
}
NEXT_CHECK = {
    'SETUP': 'Standard Pivotを確認。Early / Cheatは別の抵抗帯と構造的Stopを確認',
    'BREAKOUT': '突破価格・出来高・Gap・initial stopを再確認',
    'EXTENDED': '新規Entryは待機。押し・支持再テスト・新しい収縮を待つ',
    'PULLBACK': '21EMA等の支持、売り圧力低下、反発トリガーと押し安値を確認',
    'RETEST': '元Pivotの支持転換、再突破トリガーと再テスト安値を確認',
    '3WT': '3完了週の構造、継続Pivotと直近支持を確認',
    'TIGHT': '短期収縮の上限、継続Pivotと直近支持を確認',
    'ASCENDING_BASE': '新しいBase上限・Pivotと最新の構造的Stopを確認',
    'FAILED_BREAKOUT': 'Entry無効。新Base形成時は新しいepisodeとして再評価',
    'UNASSESSED': 'チャート型・現在状態・Pivotを確認',
}
PATTERN_CHECKS = {
    'VCP': ['contractionsDecreasing', 'volumeDryUp', 'finalContractionClear'],
    'CWH': ['cupStructure', 'handleStructure', 'handleResistanceClear'],
    'Base Breakout': ['baseStructure', 'resistanceClear', 'rightSideStructure'],
}


def positive(value):
    return finite(value) and value > 0


def dated(value, target):
    try:
        return date.fromisoformat(value) <= date.fromisoformat(target)
    except (TypeError, ValueError):
        return False


def risk_pct(entry, stop):
    return round(100 * (entry-stop)/entry, 4) if positive(entry) and positive(stop) and stop < entry else None


def load_pre_setup(root: Path, target: str):
    """Use the latest saved evaluation at/before target, not current membership."""
    path = root/'data/pre-setup/latest.json'
    if not path.exists():
        return None
    manifest = json.loads(path.read_text())
    entries = [e for e in manifest.get('entries', []) if dated(e.get('asOf'), target)]
    if not entries:
        return None
    entry = max(entries, key=lambda e: e['asOf'])
    doc = json.loads((root/'data'/entry['path']).read_text())
    if (doc.get('mode') != 'live' or doc.get('asOf') != entry['asOf']
            or doc.get('evaluationVersion') != entry.get('evaluationVersion')
            or not dated(doc.get('universeAsOf'), doc['asOf'])):
        raise ValueError('Pre-Setup manifest/date/version/universe mismatch')
    return doc


def reviewed_origin(state, registry_asof, target):
    """A registry review is additive; old confirmed types remain intact."""
    review = state.get('setupReview') or {}
    if not dated(registry_asof, target) or not dated(review.get('reviewedAsOf'), registry_asof):
        return None
    if not review.get('episodeId') or review.get('setup_type') != state.get('setup_type'):
        return None
    pivot = review.get('originPivot') or {}
    if (not pivot.get('id') or not positive(pivot.get('price')) or pivot.get('confirmed') is not True
            or not dated(pivot.get('asOf'), review['reviewedAsOf']) or not pivot.get('source')):
        return None
    return review


def promotion_checks(state, review):
    kind = state.get('setup_type')
    checks = (review or {}).get('patternChecks') or {}
    plan = next((p for p in state.get('entryPlans', []) if p.get('kind') == 'STANDARD'
                 and review and p.get('episodeId') == review['episodeId']
                 and p.get('originPivotId') == review['originPivot']['id']
                 and (p.get('pivot') or {}).get('id') == review['originPivot']['id']
                 and (p.get('pivot') or {}).get('price') == review['originPivot']['price']
                 and (p.get('pivot') or {}).get('confirmed') is True
                 and (p.get('pivot') or {}).get('source')
                 and dated((p.get('pivot') or {}).get('asOf'), p.get('asOf'))
                 and positive(p.get('entry')) and p['entry'] >= review['originPivot']['price']
                 and p.get('lifecycle') == 'SETUP'
                 and p.get('confirmed') is True and p.get('source')
                 and p.get('stopBasis') and dated(p.get('asOf'), review['reviewedAsOf'])
                 and risk_pct(p.get('entry'), p.get('stop')) is not None), None)
    return {
        'chartTypeConfirmed': kind in VALID_SETUP_TYPES and state.get('setupConfirmed') is True,
        'patternReviewed': kind in PATTERN_CHECKS and all(checks.get(k) is True for k in PATTERN_CHECKS[kind]),
        'originPivotConfirmed': review is not None,
        'structuralStopReviewed': plan is not None,
        'preBreakoutStateConfirmed': state.get('lifecycle') == 'SETUP' and state.get('lifecycleConfirmed') is True,
    }


def entry_plan(state, review, lifecycle, confirmed, target):
    allowed = ENTRY_KINDS.get(lifecycle, [])
    plan = {'lifecycle': lifecycle, 'status': 'REVIEW_REQUIRED', 'alternatives': [],
            'nextCheck': NEXT_CHECK.get(lifecycle, NEXT_CHECK['UNASSESSED'])}
    if confirmed and lifecycle in ['EXTENDED', 'FAILED_BREAKOUT']:
        plan['status'] = 'WAIT' if lifecycle == 'EXTENDED' else 'INVALID'
    for saved in state.get('entryPlans', []):
        item = {k: saved.get(k) for k in ['id', 'episodeId', 'originPivotId', 'pivot', 'lifecycle', 'kind', 'asOf',
                'source', 'entry', 'stop', 'stopBasis', 'confirmed', 'trigger', 'invalidation']}
        item['riskPct'] = risk_pct(item['entry'], item['stop'])
        compatible = (review is not None and item['episodeId'] == review['episodeId']
                      and item['originPivotId'] == review['originPivot']['id']
                      and item['lifecycle'] == lifecycle and item['kind'] in allowed)
        if not dated(item['asOf'], target):
            continue  # Future plans must not even appear as references.
        pivot = item['pivot'] or {}
        pivot_valid = (positive(pivot.get('price')) and pivot.get('id') and pivot.get('source')
                       and dated(pivot.get('asOf'), item['asOf']))
        item['status'] = ('OBSOLETE' if not compatible else 'INVALID' if item['riskPct'] is None or not pivot_valid
                          else 'CONFIRMED' if confirmed and item['confirmed'] is True
                          and item['id'] and item['source'] and item['stopBasis'] and pivot.get('confirmed') is True
                          else 'PROPOSED')
        plan['alternatives'].append(item)
    if any(p['status'] == 'CONFIRMED' for p in plan['alternatives']):
        plan['status'] = 'CONFIRMED'
    return plan


def validate_review_transition(previous, proposed, asof):
    """Validate an explicitly submitted review, without saving/promoting anything."""
    review = reviewed_origin(proposed, asof, asof)
    if review is None:
        raise ValueError('Dated episode and confirmed origin Pivot are required')
    if (proposed.get('setupConfirmed') is not True or proposed.get('lifecycleConfirmed') is not True
            or proposed.get('lifecycle') not in ENTRY_KINDS or not proposed.get('lifecycleSource')
            or not proposed.get('setupTypeSource')):
        raise ValueError('An explicit chart review must confirm both axes and retain sources')
    before = (previous or {}).get('setupReview') or {}
    if before.get('episodeId') == review['episodeId']:
        if before.get('originPivot') != review['originPivot'] or before.get('setup_type') != review['setup_type']:
            raise ValueError('An episode origin cannot be rewritten; create a new episode')
        if previous.get('lifecycle') in POST_BREAKOUT and proposed.get('lifecycle') == 'SETUP':
            raise ValueError('Reformation requires a new episode')
    elif before.get('episodeId') and review.get('previousEpisodeId') != before['episodeId']:
        raise ValueError('A new episode must link its predecessor')
    if proposed.get('lifecycle') == 'SETUP' and not all(promotion_checks(proposed, review).values()):
        raise ValueError('Formal promotion requires pattern, Pivot, Standard Entry and structural Stop review')
    return proposed


def build_journey(symbol, q, state, registry_asof, pre_row, pre_meta, target):
    state = state if dated(registry_asof, target) else {}
    review = reviewed_origin(state, registry_asof, target)
    lifecycle = q.get('lifecycle', 'UNASSESSED')
    confirmed = (q.get('lifecycleConfirmed') is True and q.get('lifecycleSource') != 'RULE_CANDIDATE'
                 and dated(registry_asof, target) and state.get('lifecycleConfirmed') is True
                 and state.get('lifecycle') == lifecycle)
    origin_confirmed = (q.get('setupConfirmed') is True and q.get('setup_type') in VALID_SETUP_TYPES
                        and state.get('setupConfirmed') is True and state.get('setup_type') == q.get('setup_type'))
    phase = 'UNASSESSED'
    if confirmed and origin_confirmed:
        phase = ('FORMAL_SETUP' if lifecycle == 'SETUP' else 'REFORMING' if lifecycle == 'FAILED_BREAKOUT'
                 else 'POST_BREAKOUT' if lifecycle in POST_BREAKOUT else 'UNASSESSED')
    pre = None
    if pre_row and pre_meta and dated(pre_meta.get('asOf'), target):
        pre = {k: pre_row.get(k) for k in ['readiness', 'candidateEligible', 'pivot', 'pivotDistancePct',
                'candidateEntry', 'candidateStop', 'marketDataAsOf', 'reasons']}
        pre.update(asOf=pre_meta['asOf'], evaluationVersion=pre_meta['evaluationVersion'],
                   stale=pre_meta['asOf'] != target)
        if (phase == 'UNASSESSED' and pre['candidateEligible'] is True and not pre['stale']
                and pre.get('marketDataAsOf') == pre_meta['asOf'] and positive(pre.get('pivot'))):
            phase = 'PRE_SETUP'
    checks = promotion_checks(state, review)
    plan = entry_plan(state, review, lifecycle, confirmed, target)
    # Candidate observations request re-review; they never mutate saved lifecycle.
    candidate = q.get('lifecycleCandidate')
    conflict = candidate not in [None, 'UNASSESSED', lifecycle]
    if conflict and plan['status'] == 'CONFIRMED':
        plan['status'] = 'REVIEW_REQUIRED'
    if phase in ['UNASSESSED', 'PRE_SETUP'] and plan['status'] == 'CONFIRMED':
        plan['status'] = 'REVIEW_REQUIRED'
    market_data_current = positive(q.get('price')) and q.get('asOf') == target
    if not market_data_current and plan['status'] == 'CONFIRMED':
        plan['status'] = 'REVIEW_REQUIRED'
    return {
        'schemaVersion': 1, 'modelVersion': MODEL_VERSION, 'asOf': target, 'symbol': symbol,
        'phase': phase, 'episodeId': review['episodeId'] if review else None,
        'previousEpisodeId': review.get('previousEpisodeId') if review else None,
        'reviewedAsOf': review.get('reviewedAsOf') if review else None,
        'marketDataAsOf': q.get('asOf'), 'marketDataCurrent': market_data_current,
        'preSetup': pre,
        'originPivot': review['originPivot'] if review else None,
        'promotion': {'requirements': checks, 'reviewComplete': all(checks.values()),
                      'automaticPromotion': False},
        'lifecycle': {'value': lifecycle, 'confirmed': confirmed, 'candidate': candidate,
                      'candidateReasons': q.get('lifecycleCandidateReasons', []), 'reviewRequired': conflict},
        'entryPlan': plan,
    }
