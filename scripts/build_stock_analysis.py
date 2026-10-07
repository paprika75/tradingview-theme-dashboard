"""Dated technical research logs for the public monitoring universe.

Does not infer a manual chart review, overwrite snapshots, or ingest positions.
Unfetched symbols stay explicitly UNANALYZED in the coverage index.
"""
import argparse
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
from research_store import atomic_json, immutable_json, timestamp, research_day, safe_path
from setup_lifecycle import load_registry_for_date
from setup_journey import build_journey, load_pre_setup

ROOT = Path(__file__).resolve().parents[1]
VERSION = '1.0.0-technical-analysis-history'
PUBLIC_LISTS = {'🇺🇸一次スクリーナー','🇯🇵一次スクリーナー','🇺🇸プレセットアップ','🇯🇵プレセットアップ',
                '🇺🇸セットアップ','🇯🇵セットアップ','❤️ブレイクアウト','💙ブレイクアウト'}


def create_entry(symbol, stock, theme, state, registry, pre_row, pre_doc, asof, generated, reason, snapshot_path, snapshot):
    q = dict(stock.get('quantitative') or {})
    # Separate contemporary manual state from older technical observations.
    for key in ['setup_type','setupConfirmed','setupTypeSource','lifecycle','lifecycleConfirmed','lifecycleSource']:
        if key in state:
            q[key] = state[key]
    q.setdefault('lifecycle', 'UNASSESSED')
    journey = build_journey(symbol, q, state, registry.get('asOf'), pre_row, pre_doc, asof)
    reviewed = [p for p in journey['entryPlan']['alternatives'] if p['status']=='CONFIRMED'] if journey['entryPlan']['status']=='CONFIRMED' else []
    plan = reviewed[0] if reviewed else {}
    pivot = journey.get('originPivot') or ({'price':pre_row.get('pivot'),'confirmed':False} if pre_row else {})
    observed = q.get('asOf')
    stale = observed != asof
    entry = {'analysisDate':asof,'marketDataAsOf':observed,'generatedAt':generated,'mode':'live',
             'evaluationVersion':VERSION,'technicalVersion':snapshot['evaluationVersion'],
             'analysisKind':'TECHNICAL_MODEL','status':'REVIEW_REQUIRED','stage':q.get('stage') or 'UNASSESSED',
             'setup':q.get('setup') or 'UNASSESSED','setup_type':q.get('setup_type'),
             'setupConfirmed':q.get('setupConfirmed') is True,'setupTypeSource':q.get('setupTypeSource'),
             'lifecycle':journey['lifecycle']['value'],'lifecycleConfirmed':journey['lifecycle']['confirmed'],
             'lifecycleSource':q.get('lifecycleSource'),'lifecycleCandidate':q.get('lifecycleCandidate'),
             'readiness':(pre_row or {}).get('readiness'),'price':q.get('price'),
             'pivot':{'value':pivot.get('price'),'label':'確認済み元Pivot' if pivot.get('confirmed') else '未確認Pivot候補'},
             'structuralStop':plan.get('stop'),'entry':plan.get('entry'),'riskPct':plan.get('riskPct'),
             'distanceToPivotPct':(pre_row or {}).get('pivotDistancePct'),'entryReadiness':None,
             'dataQuality':{'status':'OLDER_INPUT' if stale else 'OBSERVED','manualChartReview':False},
             'summary':f'{observed}までの保存済み技術データを用いた監視メモ。チャート型の自動確定はしません。',
             'idealPath':[journey['entryPlan']['nextCheck']],
             'confirmation':['直近の確定足で構造と出来高を再確認','Lifecycle別のPivot・Entry・構造的Stopをチャート確認'],
             'invalidation':['確認した支持帯の崩れ、またはブレイク仮説の無効化で再評価'],
             'action':{'code':journey['entryPlan']['status'],'label':'データ更新・チャート確認' if stale else 'チャート確認',
                       'detail':journey['entryPlan']['nextCheck']},
             'setupJourney':journey,'changeReason':reason,
             'source':{'label':'保存済みObserved技術評価 / dated Setup Registry',
                       'snapshotPath':snapshot_path,'snapshotGeneratedAt':snapshot['generatedAt'],
                       'registryAsOf':registry.get('asOf'),'preSetupAsOf':(pre_doc or {}).get('asOf')},
             'theme':theme.get('name')}
    if observed is None:
        raise ValueError('Analysis requires an observed market-data date')
    encoded = json.dumps(entry, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()
    entry['id'] = hashlib.sha256(encoded).hexdigest()[:24]
    return entry


def build(universe, generated_at, change_reason, root=ROOT):
    if timestamp(generated_at)>datetime.now(timezone.utc):
        raise ValueError('Generation timestamp cannot be in the future')
    asof = research_day(generated_at)
    if not change_reason or universe['asOf'] > asof or timestamp(universe['observedAt']) > timestamp(generated_at):
        raise ValueError('A dated universe available before generation and a change reason are required')
    targets = {}
    for record in universe['lists']:
        if record['name'] not in PUBLIC_LISTS:
            raise ValueError('Only named public research lists are accepted')
        for symbol in record['symbols']:
            market = 'JP' if symbol.startswith('TSE:') else 'US'
            if not symbol.startswith(('TSE:','NASDAQ:','NYSE:','AMEX:')) or record['market'] != market:
                raise ValueError('Invalid research symbol/market')
            targets.setdefault(symbol, {'market':market,'memberships':[]})['memberships'].append(record['name'])
    live = json.loads((root/'data/live/latest.json').read_text())
    choices = sorted([e for e in live['daily'] if e['asOf'] <= asof],key=lambda e:e['asOf'],reverse=True)
    snapshot = None
    for selected in choices:
        candidate = json.loads(safe_path(root/'data',selected['path']).read_text())
        if (candidate.get('mode')=='live' and candidate['asOf']==selected['asOf']
                and timestamp(candidate['generatedAt'])<=timestamp(generated_at)):
            snapshot = candidate
            break
    if snapshot is None:
        raise ValueError('No available Observed snapshot; keep the previous index')
    stocks = {}
    for market, market_doc in snapshot['markets'].items():
        for theme in market_doc['themes']:
            for stock in theme['stocks']:
                stocks.setdefault(stock['symbol'], (stock,theme))
                targets.setdefault(stock['symbol'], {'market':market,'memberships':['Theme catalogue']})
    registry = load_registry_for_date(root, asof)
    pre_doc = load_pre_setup(root, asof)
    pre_rows = {r['symbol']:r for m in (pre_doc or {}).get('markets',{}).values() for r in m.get('stocks',[])}
    path = root/'data/stock-analysis/manifest.json'
    previous = json.loads(path.read_text()) if path.exists() else {'schemaVersion':2,'symbols':{}}
    if previous.get('updatedAt') and timestamp(previous['updatedAt']) > timestamp(generated_at):
        raise ValueError('Cannot roll the analysis index back to an older generation')
    metadata = dict(previous['symbols'])
    for symbol,info in metadata.items():
        if not info.get('market') and info.get('path'):
            legacy=json.loads(safe_path(root,info['path']).read_text())
            if legacy.get('symbol')!=symbol:
                raise ValueError('Legacy analysis symbol mismatch')
            info['market']=legacy['market']
            info['coverageStatus']='LEGACY_ONLY'
            info['coverageReason']='以前の保存分析。今回の対象Universeでは未収集'

    batch = {'schemaVersion':2,'mode':'live','analysisDate':asof,'generatedAt':generated_at,
             'universeAsOf':universe['asOf'],'universeObservedAt':universe['observedAt'],
             'evaluationVersion':VERSION,'symbols':{}}
    for symbol, target in sorted(targets.items()):
        old = metadata.get(symbol,{})
        info = {**old,**target,'universeAsOf':asof,'coverageStatus':'UNANALYZED',
                'coverageReason':'OHLCV未取得、または技術評価に必要なデータ不足'}
        stock, theme = stocks.get(symbol, ({},{}))
        q = stock.get('quantitative') or {}
        if isinstance(q.get('price'), (int,float)) and q['price']>0 and q.get('asOf') and q['asOf']<=asof:
            analysis = create_entry(symbol,stock,theme,registry['symbols'].get(symbol,{}) or {},registry,
                                    pre_rows.get(symbol),pre_doc,asof,generated_at,change_reason,selected['path'],snapshot)
            batch['symbols'][symbol] = analysis
            info.update(coverageStatus=analysis['dataQuality']['status'],coverageReason=f"保存済み市場データ {q['asOf']}")
        metadata[symbol] = info
    paths=[]
    symbols=list(batch['symbols'])
    for offset in range(0,max(1,len(symbols)),40):
        chunk={**batch,'symbols':{s:batch['symbols'][s] for s in symbols[offset:offset+40]}}
        digest=hashlib.sha256(json.dumps(chunk,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:24]
        relative=f'stock-analysis/logs/{asof}/{digest}.json'
        paths.append(relative)
        for symbol,analysis in chunk['symbols'].items():
            info=metadata[symbol]
            records={e['id']:e for e in info.get('entries',[])}
            records[analysis['id']]={'id':analysis['id'],'path':'data/'+relative,'analysisDate':asof,
                                     'generatedAt':generated_at,'marketDataAsOf':analysis['marketDataAsOf']}
            info['entries']=sorted(records.values(),key=lambda e:(e['generatedAt'],e['id']))
            info['latestAnalysisDate']=asof
            info['marketDataAsOf']=analysis['marketDataAsOf']
        # Only the index is mutable. An interrupted run leaves immutable orphan
        # chunks which can be reused on retry; it never publishes a partial index.
        immutable_json(root/'data'/relative,chunk)
    manifest = {'schemaVersion':2,'mode':'live','updatedAt':generated_at,'evaluationVersion':VERSION,
                'universeAsOf':asof,'universeObservedAt':universe['observedAt'],'symbols':metadata}
    atomic_json(path, manifest)
    return {'analyzed':len(batch['symbols']),'universe':len(targets),'path':paths[0],'paths':paths}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--universe',type=Path,required=True)
    parser.add_argument('--generated-at',required=True)
    parser.add_argument('--change-reason',required=True)
    args=parser.parse_args()
    print(json.dumps(build(json.loads(args.universe.read_text()),args.generated_at,args.change_reason)))
