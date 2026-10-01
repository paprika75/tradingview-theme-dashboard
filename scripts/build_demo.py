"""Reproducible fixtures only. No market analysis is performed here."""
import json, math
from pathlib import Path
from datetime import date, timedelta
root = Path(__file__).resolve().parents[1]
sources = json.loads((root/'scripts/watchlist-source.json').read_text())
weights = {'daily':[.4,.3,.15,.15], 'weekly':[.35,.3,.2,.15]}
markets = {}
for src in sources:
    market = 'US' if '🇺🇸' in src['name'] else 'JP'
    themes = []
    for symbol in src['symbols']:
        if symbol.startswith('###'):
            themes.append({'id':f'{market.lower()}-{len(themes)}','name':symbol[3:],'symbols':[]})
        else:
            themes[-1]['symbols'].append(symbol)
    # Display the agreed AI value-chain order first in the source catalogue.
    if market == 'US':
        priorities = ['AI計算基盤・半導体','AIネットワーク・インターコネクト','光・CPO','メモリ・ストレージ','AIクラウド・ネオクラウド','データセンター電力・冷却']
        themes.sort(key=lambda t: priorities.index(t['name']) if t['name'] in priorities else 100)
    markets[market]={'source':src['name'],'sourceId':src['id'],'sourceModified':src['modified'],'themes':themes}

def fixture(period, index, key):
    output={'schemaVersion':1,'mode':'demo','period':period,'key':key,'evaluationVersion':'proposal-demo-v1','markets':{}}
    for market, info in markets.items():
        rows=[]
        for i,t in enumerate(info['themes']):
            base=86-i*1.35 if i<6 else 57+18*math.sin(i*1.51)
            wave=8*math.sin(index*.66+i*.72+(1 if period=='weekly' else 0))
            components=[round(max(12,min(99,base+wave+6*math.sin(i+j+index*.31))),1) for j in range(4)]
            score=round(sum(v*w for v,w in zip(components,weights[period])),1)
            stocks=[]
            for j,symbol in enumerate(t['symbols']):
                stocks.append({'symbol':symbol,'score':round(max(15,min(99,score+6-j*2.8)),1),'return1D':round(2.5*math.sin(index*.7+i*.6+j),2),'return1W':round(8*math.sin(index*.2+i*.4+j*.5),2),'rs':round(max(10,min(99,score+7-j*2)),1),'stage':'Stage 2' if (i+j)%4 else '要確認','setup':['VCP','CWH','Base Breakout',None][(i+j)%4]})
            stocks.sort(key=lambda s:(-s['score'],s['symbol']))
            rows.append({**t,'score':score,'components':components,'return1D':round(2.3*math.sin(index*.7+i*.6),2),'return1W':round(6*math.sin(index*.2+i*.4),2),'return1M':round(12*math.sin(index*.12+i*.33),2),'breadth':round(max(10,min(95,score-5))),'stocks':stocks,'leader':stocks[0]['symbol'] if stocks else None,'setups':sum(s['setup'] is not None for s in stocks)})
        rows.sort(key=lambda t:(-t['score'],t['id']))
        for rank,t in enumerate(rows,1):t['rank']=rank
        output['markets'][market]={**{k:v for k,v in info.items() if k!='themes'},'themes':rows}
    return output

manifest={'schemaVersion':1,'mode':'demo','daily':[],'weekly':[]}
for period,count,start,step in [('daily',10,date(2026,9,18),1),('weekly',8,date(2026,8,7),7)]:
    dates=[]
    if period=='daily':
        dt=start
        while len(dates)<count:
            if dt.weekday()<5:dates.append(dt)
            dt+=timedelta(days=1)
    else:dates=[start+timedelta(days=step*i) for i in range(count)]
    prev=None
    for i,dt in enumerate(dates):
        key=dt.isoformat() if period=='daily' else f'{dt.isocalendar().year}-W{dt.isocalendar().week:02}'
        doc=fixture(period,i,key)
        for market in markets:
            prev_ranks={t['id']:t['rank'] for t in prev['markets'][market]['themes']} if prev else {}
            for t in doc['markets'][market]['themes']:
                t['rankChange']=prev_ranks[t['id']]-t['rank'] if t['id'] in prev_ranks else None
        path=f'{period}/{key}.json'
        (root/'data'/path).write_text(json.dumps(doc,ensure_ascii=False,indent=2))
        manifest[period].append({'key':key,'asOf':dt.isoformat(),'path':path})
        prev=doc
latest={**manifest,'latestDaily':manifest['daily'][-1]['key'],'latestWeekly':manifest['weekly'][-1]['key'],'note':'すべての評価数値・順位・履歴・LeaderはUI検証用の架空データ。テーマと構成銘柄のみTradingViewウォッチリストの実構成。'}
(root/'data/latest.json').write_text(json.dumps(latest,ensure_ascii=False,indent=2))
(root/'data/theme-catalog.json').write_text(json.dumps({'mode':'source-catalog','capturedAt':'2026-10-02T03:32:10+09:00','markets':markets},ensure_ascii=False,indent=2))
candidates={'US':[{'name':'AI創薬・ヘルスケアAI','symbols':['NASDAQ:RXRX','NASDAQ:SDGR'],'reason':'既存のバイオと分けて比較する候補例。テーマの独立性と銘柄数を確認。'},{'name':'ゲノミクス・合成生物学','symbols':['NYSE:DNA','NASDAQ:TWST'],'reason':'ゲノム・診断とは異なる事業領域の候補例。継続性と流動性を確認。'}],'JP':[{'name':'データセンター電力・冷却','symbols':['TSE:6501','TSE:6645'],'reason':'既存の電子部品や電線と分けて比較する候補例。売上への寄与を確認。'},{'name':'サイバーセキュリティ専業','symbols':['TSE:4417','TSE:2326'],'reason':'既存ソフトウェア・サイバーを分ける候補例。テーマ重複を確認。'}]}
(root/'data/candidates.json').write_text(json.dumps({'mode':'demo','markets':candidates},ensure_ascii=False,indent=2))
print('Demo fixtures generated; daily latest:',latest['latestDaily'],'weekly latest:',latest['latestWeekly'])
