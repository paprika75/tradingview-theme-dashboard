"""Point-in-time setup type / lifecycle persistence and rule-candidate classification.

Manual chart-review state always wins. Automated logic only proposes lifecycle candidates and
must never rewrite a manually saved setup origin or lifecycle without a new registry snapshot.
"""
import json
import math
from datetime import datetime
from pathlib import Path

VALID_SETUP_TYPES = {'VCP', 'CWH', 'Base Breakout'}
VALID_LIFECYCLES = {
    'SETUP', 'BREAKOUT', 'EXTENDED', 'PULLBACK', 'RETEST',
    '3WT', 'TIGHT', 'ASCENDING_BASE', 'FAILED_BREAKOUT', 'UNASSESSED'
}
POST_BREAKOUT = VALID_LIFECYCLES - {'SETUP', 'UNASSESSED'}


def finite(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def mean(values):
    return sum(values) / len(values) if values and all(finite(v) for v in values) else None


def pct_change(a, b):
    return 100 * (a / b - 1) if finite(a) and finite(b) and b > 0 else None


def load_registry_for_date(root: Path, target: str):
    """Return the latest manually saved registry at or before target."""
    manifest_path = root / 'data/setup-state/registry/manifest.json'
    if not manifest_path.exists():
        return {'asOf': None, 'symbols': {}}
    manifest = json.loads(manifest_path.read_text())
    entries = [e for e in manifest.get('entries', []) if e.get('asOf') and e['asOf'] <= target]
    if not entries:
        return {'asOf': None, 'symbols': {}}
    entry = max(entries, key=lambda e: e['asOf'])
    doc = json.loads((root / 'data' / entry['path']).read_text())
    if doc.get('asOf') != entry['asOf']:
        raise ValueError('Setup registry manifest/date mismatch')
    symbols = doc.get('symbols', {})
    for symbol, state in symbols.items():
        if state.get('setup_type') is not None and state.get('setup_type') not in VALID_SETUP_TYPES:
            raise ValueError(f'Unsupported setup_type for {symbol}')
        if state.get('lifecycle') not in VALID_LIFECYCLES:
            raise ValueError(f'Unsupported lifecycle for {symbol}')
    return {'asOf': doc['asOf'], 'symbols': symbols, 'source': doc.get('source')}


def _weekly_closes(bars):
    weeks = {}
    for bar in bars:
        day = datetime.fromisoformat(bar['date']).date()
        weeks[day.isocalendar()[:2]] = (day, bar['c'])
    rows = [weeks[k] for k in sorted(weeks)]
    if rows and rows[-1][0].weekday() < 4:
        rows = rows[:-1]
    return [close for _, close in rows]


def _three_weeks_tight(bars, max_close_change_pct):
    closes = _weekly_closes(bars)
    if len(closes) < 3:
        return False
    last = closes[-3:]
    changes = [abs(pct_change(b, a)) for a, b in zip(last, last[1:])]
    return all(finite(v) and v <= max_close_change_pct for v in changes)


def _tight_range(bars, sessions, max_range_pct):
    if len(bars) < sessions:
        return False
    recent = bars[-sessions:]
    low = min(b['l'] for b in recent)
    high = max(b['h'] for b in recent)
    return low > 0 and 100 * (high / low - 1) <= max_range_pct


def _ascending_base_candidate(q, bars, rules):
    sessions = int(rules.get('ascendingBaseWindowSessions', 60))
    if len(bars) < sessions or q.get('stage') != 'Stage 2':
        return False
    blocks = [bars[-sessions:-40], bars[-40:-20], bars[-20:]]
    if any(len(block) < 15 for block in blocks):
        return False
    lows = [min(b['l'] for b in block) for block in blocks]
    widths = [100 * (max(b['h'] for b in block) / low - 1) for block, low in zip(blocks, lows)]
    high = max(b['h'] for b in bars[-sessions:])
    near_high = finite(q.get('price')) and q['price'] >= high * (1-rules.get('ascendingBaseNearHighPct', 5)/100)
    return lows[0] < lows[1] < lows[2] and all(w <= rules.get('ascendingBaseMaxBlockRangePct', 22) for w in widths) and near_high


def lifecycle_candidate(q, bars, registry_state, rules):
    """Return one automated lifecycle candidate plus transparent reasons.

    This is an actionability candidate, not a chart-pattern confirmation.
    """
    price = q.get('price')
    entry = q.get('entry')
    ema21 = q.get('ema21')
    ma50 = q.get('ma50')
    slope50 = q.get('slope50')
    rvol = q.get('relativeVolume')
    saved = (registry_state or {}).get('lifecycle')
    has_origin = q.get('setup_type') in VALID_SETUP_TYPES
    was_post_breakout = saved in POST_BREAKOUT
    if not was_post_breakout and finite(entry) and entry > 0 and bars:
        lookback = bars[-20:]
        was_post_breakout = any(b['h'] >= entry for b in lookback)

    reasons = []
    if not finite(price) or price <= 0:
        return 'UNASSESSED', ['価格データ不足']

    if was_post_breakout and finite(entry) and entry > 0:
        failed = price <= entry * (1-rules.get('failedPivotPct', 3)/100)
        failed = failed and finite(ma50) and price < ma50
        if failed:
            return 'FAILED_BREAKOUT', ['Pivotを一定幅下回り、50DMAも下回る']
    elif was_post_breakout and finite(ma50) and finite(slope50):
        recent = bars[-3:] if len(bars) >= 3 else []
        if recent and all(b['c'] < ma50 for b in recent) and slope50 < 0:
            return 'FAILED_BREAKOUT', ['Pivot水準未保存だが、3日連続50DMA下・50DMA下向き']

    if was_post_breakout and _three_weeks_tight(bars, rules.get('threeWeeksTightClosePct', 1.5)):
        return '3WT', ['直近3完了週の終値変化がThree Weeks Tight候補閾値内']

    if was_post_breakout and _ascending_base_candidate(q, bars, rules):
        return 'ASCENDING_BASE', ['直近3ブロックの安値切り上げ・高値圏維持']

    if was_post_breakout and _tight_range(bars, int(rules.get('tightSessions', 5)), rules.get('tightRangePct', 5)):
        return 'TIGHT', ['直近の値幅がTight候補閾値内']

    if was_post_breakout and finite(entry) and entry > 0:
        distance = pct_change(price, entry)
        if finite(distance) and abs(distance) <= rules.get('retestPct', 3):
            return 'RETEST', ['元Entry/Pivot近辺を再テスト']

    if was_post_breakout and finite(ema21) and finite(ma50):
        ema_distance = pct_change(price, ema21)
        if (finite(ema_distance)
                and rules.get('pullbackEma21MinPct', -2) <= ema_distance <= rules.get('pullbackEma21MaxPct', 3)
                and price > ma50
                and (not finite(rvol) or rvol <= rules.get('pullbackMaxRvol', 1.2))):
            return 'PULLBACK', ['21EMA近辺・50DMA上・出来高過熱なし']

    if finite(entry) and entry > 0:
        distance = pct_change(price, entry)
        if finite(distance) and distance >= rules.get('extendedFromEntryPct', 10):
            return 'EXTENDED', ['Entry/Pivotからの乖離がExtended閾値以上']
    if was_post_breakout and finite(ema21):
        ema_distance = pct_change(price, ema21)
        if finite(ema_distance) and ema_distance >= rules.get('extendedFromEma21Pct', 10):
            return 'EXTENDED', ['21EMAからの乖離がExtended閾値以上']

    if finite(entry) and entry > 0:
        if price >= entry:
            return 'BREAKOUT', ['価格がEntry/Pivot以上']
        if has_origin:
            return 'SETUP', ['Setup Typeあり・価格はEntry/Pivot未満']

    if was_post_breakout:
        return 'BREAKOUT', ['ブレイク後registry銘柄。より具体的な継続形は未検出']
    if has_origin:
        return 'SETUP', ['Setup Typeあり。Pivot水準未保存または未突破']
    if q.get('setup') == 'Pullback / Retest':
        return 'PULLBACK', ['Legacy rule candidate: Pullback / Retest']
    return 'UNASSESSED', ['Lifecycle判定に必要なSetup Type / Pivot / breakout履歴が不足']


def apply_setup_state(q, bars, registry_state, rules, registry_asof=None):
    """Persist formal setup/lifecycle fields into a quantitative stock snapshot."""
    registry_state = registry_state or {}
    legacy = q.get('setup')
    setup_type = registry_state.get('setup_type')
    setup_source = None
    setup_confirmed = False

    if setup_type in VALID_SETUP_TYPES:
        setup_source = registry_state.get('setupTypeSource', 'REGISTRY')
        setup_confirmed = registry_state.get('setupConfirmed') is True
    elif legacy in VALID_SETUP_TYPES:
        setup_type = legacy
        setup_source = 'RULE_CANDIDATE'
    else:
        setup_type = None
        setup_source = 'UNASSESSED'

    q['setup_type'] = setup_type
    q['setupConfirmed'] = setup_confirmed
    q['setupTypeSource'] = setup_source
    q['setupRegistryAsOf'] = registry_asof if registry_state else None

    candidate, reasons = lifecycle_candidate(q, bars, registry_state, rules)
    q['lifecycleCandidate'] = candidate
    q['lifecycleCandidateReasons'] = reasons
    q['lifecycleRuleVersion'] = rules.get('version', 'unversioned')

    saved = registry_state.get('lifecycle')
    if saved in VALID_LIFECYCLES:
        q['lifecycle'] = saved
        q['lifecycleSource'] = registry_state.get('lifecycleSource', 'REGISTRY')
        q['lifecycleConfirmed'] = registry_state.get('lifecycleConfirmed') is True
    else:
        q['lifecycle'] = candidate
        q['lifecycleSource'] = 'RULE_CANDIDATE' if candidate != 'UNASSESSED' else 'UNASSESSED'
        q['lifecycleConfirmed'] = False

    # Preserve legacy `setup` for old consumers, but never turn Pullback/Retest into an origin type.
    if setup_type and (legacy is None or legacy == 'Pullback / Retest'):
        q['setup'] = setup_type
    return q
