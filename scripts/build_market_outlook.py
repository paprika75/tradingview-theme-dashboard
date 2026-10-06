"""Append versioned index-only outlook supplements, without changing saved theme scores."""
import argparse, json
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal
from build_live import valid_bars, finite, mean, rnd

ROOT = Path(__file__).resolve().parents[1]

def change(a, b):
    return (Decimal(str(b)) / Decimal(str(a)) - 1) * 100

def evaluate_index(bars, asof, spec, config):
    series = [b for b in bars if b['date'] <= asof]
    out = {**spec, 'asOf': series[-1]['date'] if series else None,
           'status': 'UNASSESSED', 'phase': None, 'reasons': [],
           'distributionCount': None, 'distributionEvents': [], 'recentEvents': [],
           'rally': None, 'lastFTD': None, 'transitions': [], 'priceTrend': 'UNASSESSED'}
    if len(series) < config['minimumHistory'] or series[-1]['date'] != asof:
        out['reasons'] = ['確定日の指数足または必要な価格履歴が不足']
        return out
    prices = [b['c'] for b in series]
    ma50 = mean(prices[-50:]); ma200 = mean(prices[-200:]) if len(prices) >= 200 else None
    prior50 = mean(prices[-55:-5]) if len(prices) >= 55 else None
    trend = 'UP' if prices[-1] > ma50 and prior50 and ma50 > prior50 else 'DOWN' if prices[-1] < ma50 and prior50 and ma50 < prior50 else 'MIXED'
    out.update(price=prices[-1], ma50=rnd(ma50), ma200=rnd(ma200), priceTrend=trend,
               historyStart=series[0]['date'], historySessions=len(series))
    volume_available = lambda b: finite(b.get('v')) and b['v'] > 0
    window = config['distribution']['windowSessions']
    coverage = sum(volume_available(b) for b in series[-window-1:])
    out['volumeCoverage'] = {'valid': coverage, 'required': window + 1}
    state = 'UNASSESSED'; rally = None; last_ftd = None; events = []; below50 = 0
    transitions = []
    for i in range(49, len(series)):
        b, prev = series[i], series[i-1]
        p = b['c']; ma = mean(prices[i-49:i+1])
        long_ma = mean(prices[i-199:i+1]) if i >= 199 else None
        below50 = below50 + 1 if p < ma else 0
        peak = max(x['h'] for x in series[max(0,i-config['correction']['peakSessions']+1):i+1])
        drawdown = float(change(peak, p))
        previous_long_ma = mean(prices[i-200:i]) if i >= 200 else None
        initial_correction = state == 'UNASSESSED' and ((below50 >= config['correction']['below50Sessions'] and drawdown <= -config['correction']['drawdownPct']) or (long_ma is not None and p < long_ma and ma < long_ma))
        fresh_break = (below50 == config['correction']['below50Sessions'] and drawdown <= -config['correction']['drawdownPct']) or (long_ma is not None and previous_long_ma is not None and p < long_ma and prev['c'] >= previous_long_ma)
        structural_break = initial_correction or (state in ('CONFIRMED_UPTREND','UPTREND_UNDER_PRESSURE') and fresh_break)
        old_state = state
        for e in events:
            if not e['active']: continue
            if i - e['_index'] >= window:
                e.update(active=False, removedOn=b['date'], removalReason='25_SESSION_EXPIRY')
            elif i > e['_index'] and Decimal(str(b['h'])) >= Decimal(str(e['close'])) * (1 + Decimal(str(config['distribution']['recoveryPct']))/100):
                e.update(active=False, removedOn=b['date'], removalReason='PRICE_RECOVERY')
        volume_up = volume_available(b) and volume_available(prev) and b['v'] > prev['v']
        pct = change(prev['c'], p)
        if pct <= -Decimal(str(config['distribution']['minimumDeclinePct'])) and volume_up:
            events.append({'date': b['date'], 'close': p, 'changePct': rnd(float(pct),3),
                           'volumeRatio': rnd(b['v']/prev['v'],3), 'active': True,
                           'removedOn': None, 'removalReason': None, '_index': i})
        failed_ftd = last_ftd is not None and last_ftd['valid'] and b['l'] < last_ftd['low']
        failed_rally = rally is not None and b['l'] < rally['low']
        if structural_break or failed_ftd or failed_rally:
            state = 'MARKET_IN_CORRECTION'; rally = None
            if last_ftd and last_ftd['valid']:
                last_ftd.update(valid=False, invalidatedOn=b['date'])
        # Until a correction has been observed, do not invent an initial confirmed rally.
        if state == 'MARKET_IN_CORRECTION':
            if rally is None and p > prev['c']:
                rally = {'date': b['date'], 'low': b['l'], '_index': i}
            if rally:
                rally_day = i - rally['_index'] + 1
                if rally_day >= config['followThrough']['minimumRallyDay'] and pct >= Decimal(str(config['followThrough']['minimumGainPct'])) and volume_up:
                    last_ftd = {'date': b['date'], 'low': b['l'], 'rallyStart': rally['date'],
                                'rallyDay': rally_day, 'gainPct': rnd(float(pct),3),
                                'volumeRatio': rnd(b['v']/prev['v'],3), 'valid': True,
                                'invalidatedOn': None}
                    state = 'CONFIRMED_UPTREND'; rally = None
                    for e in events:
                        if e['active']: e.update(active=False, removedOn=b['date'], removalReason='FTD_RESET')
        if state in ('CONFIRMED_UPTREND', 'UPTREND_UNDER_PRESSURE'):
            active = [e for e in events if e['active']]
            cluster = sum(i-e['_index'] < config['pressure']['clusterSessions'] for e in active)
            pressure = p < ma or len(active) >= config['pressure']['distributionCount'] or cluster >= config['pressure']['clusterCount']
            state = 'UPTREND_UNDER_PRESSURE' if pressure else 'CONFIRMED_UPTREND'
        if old_state != state:
            transitions.append({'date': b['date'], 'from': old_state, 'to': state})
    clean = lambda e: {k: v for k,v in e.items() if not k.startswith('_')}
    out.update(lastFTD=last_ftd, transitions=transitions[-20:])
    if coverage < window + 1:
        out['reasons'] = ['指数の出来高が不足：売り抜け日・FTDを判定できません。価格トレンドは別表示']
        out['lastFTD'] = None
        return out
    active = [e for e in events if e['active']]
    recent = [e for e in events if len(series)-1-e['_index'] < 2*window]
    out.update(status=state, distributionCount=len(active), distributionEvents=[clean(e) for e in active],
               recentEvents=[clean(e) for e in recent],
               phase='RALLY_ATTEMPT' if state == 'MARKET_IN_CORRECTION' and rally else None,
               rally={**clean(rally),'day':len(series)-rally['_index']} if rally else None)
    if state == 'UNASSESSED':
        out['reasons'] = ['取得履歴内で調整→FTDの確認が完了していません。初期状態を上昇確認済みと仮定しません']
    elif state == 'MARKET_IN_CORRECTION':
        out['reasons'] = ['価格構造の悪化または上昇確認の失敗。新しいFTDを待つ局面']
    elif state == 'UPTREND_UNDER_PRESSURE':
        out['reasons'] = ([f"終値が50日移動平均を下回る"] if prices[-1] < ma50 else []) + ([f"売り抜け日{len(active)}日：警戒閾値{config['pressure']['distributionCount']}日以上"] if len(active) >= config['pressure']['distributionCount'] else []) + ([f"直近{config['pressure']['clusterSessions']}営業日に売り抜け日が{config['pressure']['clusterCount']}日以上集中"] if sum(len(series)-1-e['_index'] < config['pressure']['clusterSessions'] for e in active) >= config['pressure']['clusterCount'] else [])
    else:
        out['reasons'] = ['調整後のFTDを確認し、現在は価格構造・売り抜け日による警戒条件に該当しません']
    return out

def aggregate(indices):
    if not indices or any(x['status'] == 'UNASSESSED' for x in indices):
        return 'UNASSESSED'
    for status in ['MARKET_IN_CORRECTION','UPTREND_UNDER_PRESSURE','CONFIRMED_UPTREND']:
        if any(x['status'] == status for x in indices): return status
    return 'UNASSESSED'

def save_append_only(path, doc):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        if json.loads(path.read_text()) != doc: raise ValueError(f'Refusing to replace outlook: {path}')
        return
    path.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n')

def build(input_path):
    source = json.loads(input_path.read_text()); config = json.loads((ROOT/'config/market-outlook.json').read_text())
    manifest_path = ROOT/'data/live/latest.json'; manifest = json.loads(manifest_path.read_text())
    fetched = datetime.fromisoformat(source['fetchedAt'].replace('Z','+00:00'))
    dates = sorted({e['asOf'] for p in ['daily','weekly'] for e in manifest[p]})
    entries = []
    for date in dates:
        previous = next((e for e in manifest.get('marketOutlook',[]) if e['asOf']==date),None)
        if previous:
            saved=json.loads((ROOT/'data'/previous['path']).read_text())
            if saved['mode']!='live' or saved['asOf']!=date or saved['evaluationVersion']!=previous['evaluationVersion']:
                raise ValueError('Saved outlook manifest mismatch')
            if saved['evaluationVersion']==config['version'] and saved['rules']!=config:
                raise ValueError('Change the outlook version before changing its rules')
            entries.append(previous)
            continue
        markets = {}
        for market,specs in config['indices'].items():
            indices = [evaluate_index(valid_bars(source['documents'].get(spec['symbol'],{}),market,fetched,spec['symbol']),date,spec,config) for spec in specs]
            markets[market] = {'status':aggregate(indices),'indices':indices,'requiredIndices':[s['symbol'] for s in specs]}
        doc = {'schemaVersion':1,'mode':'live','asOf':date,'evaluationVersion':config['version'],
               'calculatedAt':source['fetchedAt'],'source':source['source'],
               'provenance':'Retrospective index calculation from completed bars, not a previously published market call',
               'rules':config,'markets':markets}
        relative = f"live/market-outlook/{config['version']}/{date}.json"
        save_append_only(ROOT/'data'/relative,doc)
        entries.append({'asOf':date,'path':relative,'evaluationVersion':config['version']})
    # Separate supplements preserve the existing daily/weekly scores and their historical config.
    manifest['marketOutlook'] = entries
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print('Generated index outlook supplements:', ', '.join(dates))

if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--input',type=Path,required=True)
    build(parser.parse_args().input)
