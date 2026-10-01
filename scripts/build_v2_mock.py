"""Generate explicitly retrospective Mock fixtures; no live AI judgments or quotes.
Existing v1 data and previously generated v2 snapshots are never overwritten.
"""
import json, math
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from datetime import datetime
root=Path(__file__).resolve().parents[1]
config=json.loads((root/'config/scoring.json').read_text())
cat=json.loads((root/'data/theme-catalog.json').read_text())
old=json.loads((root/'data/legacy-manifest.json').read_text())
assets_us=[('spx','S&P 500','EQUITY','SPCFD:SPX',6150),('ndx','NASDAQ 100','EQUITY','NASDAQ:NDX',22340),('sox','SOX','EQUITY','NASDAQ:SOX',5430),('rut','Russell 2000','EQUITY','TVC:RUT',2320),('fang','FANG+','EQUITY','NYSE:NYFANG',13120),('us10y','US 10Y Yield','RATES / FX','TVC:US10Y',4.15),('us2y','US 2Y Yield','RATES / FX','TVC:US02Y',3.92),('spread','10Y−2Y Spread','RATES / FX',None,.23),('dxy','DXY','RATES / FX','TVC:DXY',101.4),('wti','WTI Crude Oil','CROSS ASSET','TVC:USOIL',73.2),('gold','Gold','CROSS ASSET','OANDA:XAUUSD',2670),('btc','BTC','CROSS ASSET','CRYPTO:BTCUSD',98500),('vix','VIX','CROSS ASSET','TVC:VIX',18.4)]
assets_jp=[('nikkei','日経225','EQUITY','TVC:NI225',41320),('topix','TOPIX','EQUITY','TSE:TOPIX',2850),('growth','グロース250','EQUITY','TSE:MOS',752),('usdJPY','USD / JPY','RATES / FX','FX:USDJPY',146.2)]+assets_us[5:]
extra={'US':[('us-energy','Energy',['NYSE:XOM','NYSE:CVX']),('us-oil-services','Oil Services',['NYSE:SLB','NYSE:HAL']),('us-gold','Gold Miners',['NYSE:NEM','NYSE:AEM']),('us-utilities','Utilities',['NYSE:NEE','NYSE:DUK'])],'JP':[('jp-energy','エネルギー・石油',['TSE:1605','TSE:1662']),('jp-gold','金・貴金属',['TSE:5713','TSE:5711']),('jp-utilities','電力・ユーティリティ',['TSE:9503','TSE:9502'])]}
for market in cat['markets']:
 for tid,name,symbols in extra[market]:cat['markets'][market]['themes'].append({'id':tid,'name':name,'symbols':symbols,'catalogOrigin':'mock-extension'})

def weighted(vals,weights):
 total=sum(Decimal(str(v)) for v in weights.values())
 result=sum(Decimal(str(max(0,min(100,vals[k]))))*Decimal(str(v)) for k,v in weights.items())/total
 return float(result.quantize(Decimal('0.1'),rounding=ROUND_HALF_UP))
def dump(path,data):
 p=root/path;p.parent.mkdir(parents=True,exist_ok=True)
 text=json.dumps(data,ensure_ascii=False,separators=(',',':'))
 if p.exists() and p.read_text()!=text:raise RuntimeError(f'Immutable fixture exists: {p}; use a new revision namespace')
 p.write_text(text)

def all_themes(market,index,asof):
 themes=[]
 for i,t in enumerate(cat['markets'][market]['themes']):
  # Diverse scenarios deliberately include improving, extended, and deteriorating themes.
  base=85-i*.7 if i<6 else 59+17*math.sin(i*1.3)
  score=round(max(25,min(98,base+5*math.sin(index*.5+i))),1)
  above50=round(max(20,min(96,score-4)));above200=max(20,above50-4)
  breadthDelta=round(7*math.sin(i*.6+index*.3),1)
  acceleration=round(max(20,min(98,score+12*math.sin(i+index*.2))),1)
  # Stable scenarios for meaningful UI inspection.
  if t['name']=='メモリ・ストレージ':score,above50,above200,breadthDelta,acceleration=86+index*.4,84,80,9,96
  if t['name']=='AIネットワーク・インターコネクト':score,above50,above200,breadthDelta=76,61,74,-13
  extension=round(max(0,7+9*math.sin(i*.91+index*.15)),1)
  if t['name']=='メモリ・ストレージ':extension=3.2
  if t['name']=='AI計算基盤・半導体':extension=14.8
  stocks=[]
  for j,symbol in enumerate(t['symbols']):
   price=round(90+(i*31+j*13)%280,2) if market=='US' else 1200+(i*171+j*330)%9000
   rs=round(max(18,min(99,score+4-j*2.2)),1)
   stage2=(i+j)%4!=0
   c={'rs':rs,'trend':85 if stage2 else 48,'structure':round(max(25,score-j*2),1),'liquidity':max(35,90-j*3),'accumulation':max(20,78-j*2),'breakoutQuality':max(20,80-j*3),'fundamentalGrowth':max(25,75-j*2)}
   pattern=['VCP','CWH','Base Breakout','Pullback / Retest',None][(i+j)%5]
   distance=round(1.2+(j%4)*2.1,1)
   if extension>=10:distance=-extension
   stage='Stage 2' if stage2 else '要確認'
   quant={'price':price,'return1D':round(1.8*math.sin(index+i+j),2),'return1W':round(4.5*math.sin(index*.3+i+j*.2),2),'return1M':round(12*math.sin(i*.2+index*.13),2),'rs':rs,'stage':stage,'ma50':round(price/(1.035 if stage2 else .985),2),'ma150':round(price/1.06,2),'ma200':round(price/1.08,2),'above50':stage2,'volume':1200000+j*250000,'relativeVolume':round(1.1+(j%3)*.25,2),'dollarVolume':round(price*(1200000+j*250000)),'salesGrowth':18+j,'epsGrowth':24+j*2,'extensionPct':extension,'setup':pattern,'pivotDistancePct':distance,'entry':round(price*(1+distance/100),2),'stop':round(price*(1+distance/100)*.95,2),'setupReady':bool(pattern and 0<=distance<=3.5 and stage2)}
   stocks.append({'symbol':symbol,'quantitative':quant,'scores':{'leader':weighted(c,config['leader']),'components':c}})
  stocks.sort(key=lambda s:(-s['scores']['leader'],s['symbol']))
  ready=sum(s['quantitative']['setupReady'] for s in stocks)
  if t['name']=='メモリ・ストレージ':ready=sum(s['quantitative']['setupReady'] for s in stocks)
  q={'return1D':round(1.7*math.sin(index*.7+i*.6),2),'return1W':round(5*math.sin(index*.2+i*.4),2),'return1M':round(14*math.sin(index*.12+i*.33),2),'relativeStrength':round(max(10,min(99,score+3)),1),'momentum':score,'dailyAcceleration':acceleration,'above50':above50,'above200':above200,'stage2Ratio':round(sum(s['quantitative']['stage']=='Stage 2' for s in stocks)*100/len(stocks)),'breadthDelta5':breadthDelta,'leaderRSDelta5':round(breadthDelta*.45,1),'relativeVolume':round(1.1+(i%4)*.18,2),'accumulationDays':3+i%4,'distributionDays':i%5,'breakouts':max(1,len(stocks)//2),'failedBreakouts':int(i%6==0),'followThroughPct':round(2.2+3*math.sin(i),1),'setupCount':sum(bool(s['quantitative']['setup']) for s in stocks),'setupReady':ready,'extensionPct':extension,'weeklyDelta5':-11 if t['name']=='AIネットワーク・インターコネクト' else round(breadthDelta*.8,1),'weeklyDelta3Weeks':-18 if i%11==9 else round(5*math.sin(i),1),'above50History':[max(10,above50-breadthDelta),above50-breadthDelta/2,above50],'rsHistory':[score-3,score-1,score+3]}
  daily={'momentum':q['dailyAcceleration'],'breadth':above50,'participation':min(100,q['relativeVolume']*50),'leaderQuality':stocks[0]['scores']['leader']}
  weekly={'relativeStrength':q['relativeStrength'],'trendBreadth':above200,'trendQuality':q['stage2Ratio'],'actionability':min(100,ready*25)}
  themes.append({**t,'category':'AI / '+['Compute','Network','Optical','Memory','Cloud','Power / Cooling'][i] if i<6 and market=='US' else 'Other','quantitative':q,'scores':{'daily':weighted(daily,config['daily']),'weekly':weighted(weekly,config['weekly']),'leaderQuality':stocks[0]['scores']['leader'],'dailyComponents':daily,'weeklyComponents':weekly},'stocks':stocks})
 for period in ['daily','weekly']:
  ranked=sorted(themes,key=lambda t:(-t['scores'][period],t['id']))
  for rank,t in enumerate(ranked,1):t['quantitative'][period+'Rank']=rank
 for i,t in enumerate(themes):t['quantitative']['weeklyRankChange']=2 if t['name'] in ['メモリ・ストレージ','Gold Miners'] else (-2 if i%3==0 else 1)
 return themes

manifest={'schemaVersion':2,'mode':'mock','generatedAt':'2026-10-02T04:40:26+09:00','daily':[],'weekly':[],'description':'Mock values and retrospective AI examples only. No real past predictions.'}
days=old['daily']; all_dates=sorted(set(e['asOf'] for e in old['weekly']+days))
for index,asof in enumerate(all_dates):
 raw={'schemaVersion':2,'mode':'mock','asOf':asof,'timestamp':asof+'T16:00:00+09:00','source':'MOCK / synthetic observations','markets':{}}
 analysis={'schemaVersion':2,'mode':'mock','date':asof,'generatedAt':manifest['generatedAt'],'kind':'retrospective-mock-fixture','confidence':'MEDIUM','rawRef':f'raw/mock/{asof}.json','quantitativeRef':f'mock/daily/{asof}.json' if any(e['asOf']==asof for e in days) else None,'markets':{}}
 evaluated={}
 for market in ['US','JP']:
  assets=[]
  for n,(aid,name,group,symbol,base) in enumerate(assets_us if market=='US' else assets_jp):
   price=round(base*(1+.003*math.sin(index+n)),2 if base>10 else 3)
   ret1=round(1.2*math.sin(n+index*.3),2); retw=round(3*math.sin(n*.7+index*.2),2);retm=round(8*math.sin(n*.4+index*.13),2)
   # Coherent macro scenarios for UI testing; these are not observed quotes.
   if aid=='gold':ret1,retw,retm=.85,3.2,7.6
   if aid=='dxy':ret1,retw,retm=-.32,-1.3,-3.1
   if aid in ['us10y','us2y']:ret1,retw,retm=(3.2,9,16) if aid=='us10y' else (1.4,4,7)
   a={'id':aid,'name':name,'group':group,'symbol':symbol,'price':price,'change1D':ret1,'change1W':retw,'change1M':retm,'ma21':round(price/(1+retw/160),3),'ma50':round(price/(1+retm/150),3),'ma150':round(price/1.04,3),'ma200':round(price/1.06,3),'slope21':round(retw/4,2),'slope50':round(retm/8,2),'slope150':.8,'slope200':.6,'structure':'Higher High / Higher Low' if retm>0 else 'Lower High / Lower Low','volume':820000000+n*31000000 if group=='EQUITY' else None,'relativeVolume':1.12 if group=='EQUITY' else None,'accumulationDays':4 if group=='EQUITY' else None,'distributionDays':3+n%3 if group=='EQUITY' else None,'unit':'%' if aid in ['us10y','us2y','spread'] else ('USD' if aid in ['gold','wti','btc'] else ''),'maType':'SMA','source':'MOCK','changeUnit':'bp' if aid in ['us10y','us2y','spread'] else '%'}
   assets.append(a)
  # Yield spread uses actual arithmetic within Mock; delta in bps, not percent change.
  by={a['id']:a for a in assets};spread=by['spread'];spread['price']=round(by['us10y']['price']-by['us2y']['price'],3)
  for key in ['change1D','change1W','change1M']:
   spread[key]=round(by['us10y'][key]-by['us2y'][key],1)
  for aid in ['us10y','us2y','spread']:
   a=by[aid]
   a['ma21']=round(a['price']-a['change1W']/100*.5,3);a['ma50']=round(a['price']-a['change1M']/100*.6,3)
   a['slope21']=.1 if a['change1W']>0 else -.1;a['slope50']=.2 if a['change1M']>0 else -.2
  raw['markets'][market]={'assets':assets,'breadth':{'advancing':1732 if market=='US' else 1023,'declining':1268 if market=='US' else 641,'newHigh':147,'newLow':61,'above50':68,'above200':73},'leadership':{'leaderRS':84,'stage2Ratio':72,'strongThemeCount':11,'leadersAbove50':79},'breakoutQuality':{'success':18,'failed':7,'followThrough':62,'setupBreakoutReturn':3.4,'sampleWindow':'20 trading sessions / MOCK'}}
  themes=all_themes(market,index,asof)
  health={'trend':82 if market=='US' else 76,'institutionalAction':68,'breadth':72,'leadership':81,'breakoutQuality':66}
  evaluated[market]={'source':cat['markets'][market]['source'],'assets':assets,'marketQuantitative':raw['markets'][market],'scores':{'marketHealth':weighted(health,config['marketHealth']),'marketComponents':health},'themes':themes,'ibdReference':{'available':False,'exposure':None,'sourceUrl':None,'reason':'実際のIBD Referenceは未取得。独自評価との乖離は未判定。'}}
  focus=[{'id':'yield','rank':1,'name':'Treasury yields / 金利','importance':'HIGH','sensitivity':'HIGH','persistence':'HIGH','confidence':'MEDIUM','impact':'Growth / Techに向かい風の可能性','reason':'Mock：金利上昇時の長期成長株の反応を監視。固定の最重要指標にはしない。','expectedImpact':'Growth / Tech Headwind','watchThemes':['AI計算基盤・半導体','AIソフト・アプリ'],'evidence':[{'type':'price reaction','text':'US10Y・DXY・NASDAQの価格反応例','rawRef':analysis['rawRef']},{'type':'strategist commentary','text':'未取得：実際の機関投資家の言及は未接続','sourceUrl':None}],'isNew':False},{'id':'ai-capex','rank':2,'name':'AI Capex / 半導体需要','importance':'HIGH','sensitivity':'HIGH','persistence':'HIGH','confidence':'MEDIUM','impact':'Memory / Networkを重点確認','reason':'Mock：需要材料だけでなく、BreadthとLeaderの裏付けを確認する場面。','expectedImpact':'Memory Tailwind','watchThemes':['メモリ・ストレージ','AIネットワーク・インターコネクト'],'evidence':[{'type':'earnings','text':'未取得：決算・Capex発言は未接続','sourceUrl':None}],'isNew':False},{'id':'gold','rank':3,'name':'Gold / Dollar','importance':'MEDIUM','sensitivity':'MEDIUM','persistence':'MEDIUM','confidence':'LOW','impact':'Gold Minersへの波及を確認','reason':'Mock：Goldの動きが鉱山株へ伝わるかを確認する例。実質金利は未取得。','expectedImpact':'Gold Miners Tailwind','watchThemes':['Gold Miners' if market=='US' else '金・貴金属'],'evidence':[{'type':'cross-asset','text':'Gold / DXYの値動き例。実質金利は入力不足','rawRef':analysis['rawRef']}],'isNew':True}]
  translations=[{'driverId':'yield','signal':'HEADWIND','themes':['us-0','us-11'] if market=='US' else ['jp-0','jp-12'],'reason':'Mock：金利・ドル高が高Duration株の評価へ与える圧力を検討。','confidence':'MEDIUM'},{'driverId':'ai-capex','signal':'POSITIVE','themes':['us-6','us-4'] if market=='US' else ['jp-5','jp-7'],'reason':'Mock：AI需要の材料をテーマへ翻訳。SetupがなければEntry候補にしない。','confidence':'MEDIUM'},{'driverId':'gold','signal':'POSITIVE','themes':['us-gold'] if market=='US' else ['jp-gold'],'reason':'Mock：金価格上昇から鉱山株への波及仮説。確認不足ならUNCONFIRMED。','confidence':'LOW'}]
  theme_ai={}
  for t in themes:
   q=t['quantitative'];negative=q['breadthDelta5']<0
   theme_ai[t['id']]={'opportunity':{'reason':'Mock：Weeklyの基礎的な強さとDailyの加速、実際にReadyなSetupを確認する候補例。既に伸びたテーマは見送り。','confidence':'MEDIUM'},'activeHealth':{'reason':'Mock：3–5営業日のBreadth低下を警戒。2–4週の中期構造とは分けて確認。' if negative else 'Mock：短期変化と中期構造を分けて監視。LeaderとBreadthの維持を確認する例。','confidence':'MEDIUM'},'macroAlignment':'HEADWIND' if t['id'] in translations[0]['themes'] else 'TAILWIND' if any(t['id'] in x['themes'] for x in translations[1:]) else 'NEUTRAL','institutionalAlignment':'HIGH' if any(t['id'] in x['themes'] for x in translations) else 'LOW'}
  analysis['markets'][market]={'regime':{'label':'SELECTIVE RISK-ON','reason':'Mock：指数トレンドは保たれる一方、Breadthとブレイクの質にはばらつき。新規EntryはSetup単位で選別。','confidence':'MEDIUM'},'focus':focus,'translations':translations,'themes':theme_ai,'activeSamples':['us-4','us-6'] if market=='US' else ['jp-2','jp-7'],'events':[{'name':'次のインフレ指標 / 雇用統計','date':None,'note':'実際のイベント日程は未取得'}]}
 dump(f'data/raw/mock/{asof}.json',raw);dump(f'data/analysis/mock/{asof}.json',analysis)
 for period in ['daily','weekly']:
  matches=[e for e in old[period] if e['asOf']==asof]
  if not matches:continue
  entry=matches[0]
  doc={'schemaVersion':2,'mode':'mock','asOf':asof,'key':entry['key'],'period':period,'timestamp':raw['timestamp'],'generatedAt':manifest['generatedAt'],'evaluationVersion':config['version'],'rawRef':f'raw/mock/{asof}.json','analysisRef':f'analysis/mock/{asof}.json','markets':evaluated}
  dump(f'data/mock/{period}/{entry["key"]}.json',doc)
  manifest[period].append({'key':entry['key'],'asOf':asof,'path':f'mock/{period}/{entry["key"]}.json','rawPath':doc['rawRef'],'analysisPath':doc['analysisRef']})
manifest['lastSuccessfulUpdate']=manifest['generatedAt'];manifest['expectedNextUpdate']=None
(root/'data/mock/latest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
(root/'data/latest.json').write_text(json.dumps({'schemaVersion':2,'mode':'mock','manifestPath':'mock/latest.json','liveManifestPath':'live/latest.json','version':'2.0.0'},indent=2))
print('Mock v2 generated:',len(manifest['daily']),'daily,',len(manifest['weekly']),'weekly. Existing v1 archives preserved.')