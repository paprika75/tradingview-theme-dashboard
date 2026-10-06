"""Append independent reference stock-exposure ranges to saved index outlooks."""
import argparse
import json
from pathlib import Path
from datetime import datetime
from build_live import valid_bars, finite
from build_market_outlook import save_append_only, aggregate

ROOT = Path(__file__).resolve().parents[1]
KNOWN = {'CONFIRMED_UPTREND', 'UPTREND_UNDER_PRESSURE', 'MARKET_IN_CORRECTION'}

def evaluate(market, asof, sessions, rules):
    result = {'band': None, 'range': None, 'reasons': [], 'inputs': []}
    indices = market.get('indices', [])
    required = market.get('requiredIndices', [])
    if (market.get('status') not in KNOWN or not required
        or len(indices) != len(required) or len(set(required)) != len(required)
        or sorted(x['symbol'] for x in indices) != sorted(required)
        or market.get('status') != aggregate(indices)
        or any(x.get('status') not in KNOWN or x.get('asOf') != asof
               or not isinstance(x.get('distributionCount'), int) or x['distributionCount'] < 0
               or any(not finite(x.get(k)) or x[k] <= 0 for k in ['price', 'ma50', 'ma200'])
               for x in indices)):
        result['reasons'] = ['必要な指数の市場区分・価格・出来高評価が不足しているため未判定']
        return result
    bands = []
    for index in indices:
        dates = [d for d in sessions.get(index['symbol'], []) if d <= asof]
        if not dates or dates[-1] != asof or len(dates) != len(set(dates)) or dates != sorted(dates):
            result['reasons'] = ['評価日に一致する指数の確定営業日データが不足']
            return result
        above50 = index['price'] > index['ma50']
        above200 = index['price'] > index['ma200']
        count = index['distributionCount']
        cluster = sum(e['date'] in dates[-rules['clusterSessions']:] for e in index['distributionEvents'])
        ftd = index.get('lastFTD')
        age = len(dates)-dates.index(ftd['date'])-1 if ftd and ftd.get('valid') and ftd['date'] in dates else None
        status = index['status']
        if status == 'MARKET_IN_CORRECTION':
            band, reason = 0, '調整局面のため0–20%'
        elif status == 'UPTREND_UNDER_PRESSURE':
            severe = not above50 or count >= rules['heavyDistributionCount'] or cluster >= rules['clusterCount']
            band = 1 if severe else 2
            triggers = []
            if not above50: triggers.append('50DMA以下')
            if count >= rules['heavyDistributionCount']: triggers.append(f'売り抜け日{count}日（強い警戒）')
            if cluster >= rules['clusterCount']: triggers.append(f"直近{rules['clusterSessions']}営業日に{cluster}日集中")
            reason = '・'.join(triggers) if severe else f'警戒局面・売り抜け日{count}日'
        else:
            if age is None:
                result['reasons'] = ['有効なFTDと確定営業日の対応を確認できないため未判定']
                return result
            thresholds = rules['ftdSessions']
            band = 1 if age < thresholds['developing'] else 2 if age < thresholds['established'] else 3
            if age >= thresholds['mature'] and above50 and above200 and index['priceTrend'] == 'UP' and count <= rules['fullExposureMaxDistributionCount']:
                band = 4
            if not above50 or not above200 or index['priceTrend'] != 'UP': band = min(band, 2)
            reason = f'FTD後{age}営業日・売り抜け日{count}日'
            if not above50 or not above200 or index['priceTrend'] != 'UP': reason += '・価格構造未確認で40–60%以下'
        bands.append(band)
        result['inputs'].append({'symbol': index['symbol'], 'name': index['name'], 'band': band,
                                'ftdSessionsElapsed': age, 'above50': above50, 'above200': above200,
                                'distributionCount': count, 'recentDistributionCount': cluster})
        result['reasons'].append(f"{index['name']}：{reason}")
    band = min(bands)
    result.update(band=band, range=rules['ranges'][band])
    result['reasons'].append('必要な指数のうち低いレンジを採用。監視銘柄の点数は使用しません')
    return result

def build(input_path):
    source = json.loads(input_path.read_text())
    rules = json.loads((ROOT/'config/market-exposure.json').read_text())
    manifest_path = ROOT/'data/live/latest.json'
    manifest = json.loads(manifest_path.read_text())
    fetched = datetime.fromisoformat(source['fetchedAt'].replace('Z', '+00:00'))
    entries = {e['asOf']: e for e in manifest.get('marketExposure', [])}
    history = {}
    for entry in sorted(manifest['marketOutlook'], key=lambda e: e['asOf']):
        date = entry['asOf']
        outlook = json.loads((ROOT/'data'/entry['path']).read_text())
        if outlook['mode'] != 'live' or outlook['asOf'] != date or outlook['evaluationVersion'] != entry['evaluationVersion']:
            raise ValueError('Saved outlook manifest mismatch')
        if date in entries:
            saved = json.loads((ROOT/'data'/entries[date]['path']).read_text())
            if saved['mode'] != 'live' or saved['asOf'] != date or saved['evaluationVersion'] != entries[date]['evaluationVersion']:
                raise ValueError('Saved exposure manifest mismatch')
            if saved['evaluationVersion'] == rules['version'] and saved['rules'] != rules:
                raise ValueError('Change the exposure version before changing its rules')
        else:
            markets = {}
            for market, value in outlook['markets'].items():
                sessions = {i['symbol']: [b['date'] for b in valid_bars(source['documents'].get(i['symbol'], {}), market, fetched, i['symbol'])] for i in value['indices']}
                result = evaluate(value, date, sessions, rules)
                previous = history.get(market)
                # Compare stored assessments, never imply a saved daily trading record.
                result['previous'] = previous
                result['change'] = (None if not previous or previous['evaluationVersion'] != rules['version'] or result['band'] is None or previous['band'] is None
                                    else result['band']-previous['band'])
                markets[market] = result
            saved = {'schemaVersion': 1, 'mode': 'live', 'asOf': date,
                     'evaluationVersion': rules['version'], 'outlookVersion': outlook['evaluationVersion'],
                     'calculatedAt': source['fetchedAt'], 'rules': rules,
                     'provenance': 'Retrospective reference range from saved index outlook; not an actual allocation',
                     'markets': markets}
            relative = f"live/market-exposure/{rules['version']}/{date}.json"
            save_append_only(ROOT/'data'/relative, saved)
            entries[date] = {'asOf': date, 'path': relative, 'evaluationVersion': rules['version']}
        for market, value in saved['markets'].items():
            history[market] = {'asOf': date, 'band': value['band'], 'range': value['range'],
                              'evaluationVersion': saved['evaluationVersion']}
    manifest['marketExposure'] = [entries[d] for d in sorted(entries)]
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    print('Generated reference exposure supplements:', ', '.join(sorted(entries)))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    build(parser.parse_args().input)
