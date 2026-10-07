"""Extract candidates from a dated primary watchlist; never amend old snapshots."""
import argparse
import json
from pathlib import Path
from datetime import datetime
from build_live import valid_bars, finite, mean, rnd
from build_market_outlook import save_append_only

ROOT = Path(__file__).resolve().parents[1]

def ratio(a, b):
    return a/b if finite(a) and finite(b) and b > 0 else None

def evaluate(symbol, bars, asof, rules):
    series = [b for b in bars if b['date'] <= asof]
    out = {'symbol': symbol, 'marketDataAsOf': series[-1]['date'] if series else None,
           'candidateEligible': False, 'readiness': 'UNASSESSED', 'setup_type': None,
           'setupConfirmed': False, 'lifecycle': 'UNASSESSED', 'reasons': [], 'metrics': {}}
    if len(series) < rules['minimumBars'] or series[-1]['date'] != asof:
        out['reasons'] = ['評価日の確定足または必要な価格履歴が不足']
        return out
    p = series[-1]['c']; prices = [b['c'] for b in series]
    ma50 = mean(prices[-50:]); prior50 = mean(prices[-55:-5])
    resistance = series[-rules['pivotSessions']-1:-1]
    pivot = max(b['h'] for b in resistance)
    distance = 100*(pivot/p-1)
    touches = sum(b['h'] >= pivot*(1-rules['pivotTouchTolerancePct']/100) for b in resistance)
    width = lambda bs: max(b['h'] for b in bs)-min(b['l'] for b in bs)
    range_ratio = ratio(width(series[-10:]), width(series[-20:-10]))
    tr = [max(b['h']-b['l'], abs(b['h']-a['c']), abs(b['l']-a['c'])) for a,b in zip(series,series[1:])]
    atr_ratio = ratio(mean(tr[-10:]), mean(tr[-20:-10]))
    volumes = [b.get('v') for b in series[-60:]]
    volume_ratio = ratio(mean(volumes[-10:]), mean(volumes[:-10])) if all(finite(v) and v > 0 for v in volumes) else None
    checks = {'rangeContraction': range_ratio is not None and range_ratio <= rules['rangeContractionRatio'],
              'atrContraction': atr_ratio is not None and atr_ratio <= rules['atrContractionRatio'],
              'volumeDryUp': volume_ratio is not None and volume_ratio <= rules['volumeDryUpRatio'],
              'pivotClear': touches >= rules['minimumPivotTouches'],
              'aboveRising50': p > ma50 and ma50 > prior50,
              'higherLow': min(b['l'] for b in series[-10:]) >= min(b['l'] for b in series[-20:-10])}
    trend = {'priceAbove50': p > ma50, 'ma50Rising': ma50 > prior50}
    for n in [150, 200]:
        trend['priceAbove'+str(n)] = p > mean(prices[-n:]) if len(prices) >= n else None
    trend['ma50Above150'] = ma50 > mean(prices[-150:]) if len(prices) >= 150 else None
    trend['ma150Above200'] = mean(prices[-150:]) > mean(prices[-200:]) if len(prices) >= 200 else None
    trend['ma200Rising21'] = mean(prices[-200:]) > mean(prices[-221:-21]) if len(prices) >= 221 else None
    trend['above52Low30'] = p >= 1.3*min(b['l'] for b in series[-252:]) if len(series) >= 252 else None
    trend['within52High25'] = p >= .75*max(b['h'] for b in series[-252:]) if len(series) >= 252 else None
    out.update(price=p, pivot=rnd(pivot), pivotDistancePct=rnd(distance),
               candidateEntry=rnd(pivot*(1+rules['entryBufferPct']/100)),
               candidateStop=rnd(min(b['l'] for b in series[-10:])),
               trendChecks=trend, checks=checks,
               metrics={'rangeRatio':rnd(range_ratio,3), 'atrRatio':rnd(atr_ratio,3),
                        'volumeRatio':rnd(volume_ratio,3), 'pivotTouches':touches})
    # Intraday passage is sent for review, never silently kept as pre-breakout.
    if series[-1]['h'] >= pivot:
        out.update(readiness='EXCLUDED', lifecycle='BREAKOUT' if p >= pivot else 'UNASSESSED')
        out['reasons'] = ['終値がPivot候補以上：Breakout側で確認' if p >= pivot else '当日高値がPivot候補に到達・通過：突破後の状態を手動確認']
        return out
    if volume_ratio is None:
        out['reasons'] = ['出来高不足。Dry-upを未判定とし、候補判定を保留']
        return out
    formation = sum(checks[k] for k in ['rangeContraction','atrContraction','volumeDryUp']) >= rules['minimumContractionChecks']
    if not (formation and checks['pivotClear'] and checks['aboveRising50'] and 0 < distance <= rules['maximumDistancePct']):
        out['readiness'] = 'EXCLUDED'
        out['reasons'] = ['収縮・明確なPivot・上向き50DMA・Pivotまでの距離の候補条件に未達']
        return out
    readiness = 'Ready' if distance <= rules['readyDistancePct'] else 'Near' if distance <= rules['nearDistancePct'] else 'Forming'
    out.update(candidateEligible=True, readiness=readiness, lifecycle='SETUP')
    out['reasons'] = ['収縮3条件のうち2条件以上・抵抗帯への複数接触・上向き50DMA上を確認',
                      'チャート型・正式Pivot・構造的Stopは未確定。チャート確認後に昇格判断']
    return out

def build(input_path, universe_path, asof):
    source = json.loads(input_path.read_text()); universe = json.loads(universe_path.read_text())
    rules = json.loads((ROOT/'config/pre-setup.json').read_text())
    if not universe.get('asOf') or universe['asOf'] > asof:
        raise ValueError('Primary universe must be saved at or before the evaluation date; do not backfill current membership')
    fetched = datetime.fromisoformat(source['fetchedAt'].replace('Z','+00:00'))
    markets = {}
    for market, entry in universe['markets'].items():
        if market not in ['US','JP']: raise ValueError('Unsupported market')
        if entry.get('name') != ('🇺🇸一次スクリーナー' if market=='US' else '🇯🇵一次スクリーナー'):
            raise ValueError('Use the primary screener universe, not holdings or other watchlists')
        symbols = list(dict.fromkeys(entry['symbols']))
        rows = []
        for symbol in symbols:
            try:
                bars = valid_bars(source['documents'].get(symbol,{}),market,fetched,symbol)
                rows.append(evaluate(symbol,bars,asof,rules))
            except (ValueError,KeyError) as error:
                rows.append({'symbol':symbol,'candidateEligible':False,'readiness':'UNASSESSED',
                             'setup_type':None,'setupConfirmed':False,'lifecycle':'UNASSESSED','reasons':[str(error)]})
        markets[market] = {'sourceList':entry['name'],'requested':len(symbols),
                           'assessed':sum(r['readiness']!='UNASSESSED' for r in rows),
                           'candidates':sum(r['candidateEligible'] for r in rows),'stocks':rows}
    doc = {'schemaVersion':1,'mode':'live','asOf':asof,'evaluationVersion':rules['version'],
           'calculatedAt':source['fetchedAt'],'universeAsOf':universe['asOf'],
           'rules':rules,'markets':markets,'notice':'定量候補。正式Setup・売買推奨ではありません'}
    path = f"pre-setup/{rules['version']}/{asof}.json"
    save_append_only(ROOT/'data'/path,doc)
    manifest_path = ROOT/'data/pre-setup/latest.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {'schemaVersion':1,'mode':'live','entries':[]}
    entry = {'asOf':asof,'path':path,'evaluationVersion':rules['version']}
    existing = next((e for e in manifest['entries'] if e['asOf']==asof),None)
    if existing and existing != entry: raise ValueError('Saved pre-setup manifest conflict')
    if not existing: manifest['entries'].append(entry)
    manifest['entries'].sort(key=lambda e:e['asOf'])
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({m:{k:v for k,v in x.items() if k!='stocks'} for m,x in markets.items()},ensure_ascii=False))

if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--universe',type=Path,required=True);parser.add_argument('--as-of',required=True)
    args=parser.parse_args();build(args.input,args.universe,args.as_of)
