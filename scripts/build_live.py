"""Build append-only observed technical snapshots from authorized TradingView OHLCV.
No network, credentials, simulated prices or generated AI prose are used here.
"""
import argparse, json, math, statistics
from pathlib import Path
from datetime import datetime, timedelta, time, timezone
from zoneinfo import ZoneInfo
from decimal import Decimal, ROUND_HALF_UP

ROOT = Path(__file__).resolve().parents[1]
VERSION = '3.1.0-daily-theme-v1'
MIN_BARS = 253

def finite(v): return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
def rnd(v, n=2): return round(v, n) if finite(v) else None
def mean(v): return statistics.mean(v) if v and all(finite(x) for x in v) else None
def clamp(v): return max(0, min(100, v)) if finite(v) else None
def weighted(v, w):
    if any(not finite(v.get(k)) for k in w): return None
    total=sum(Decimal(str(x)) for x in w.values())
    score=sum(Decimal(str(clamp(v[k])))*Decimal(str(weight)) for k,weight in w.items())/total
    return float(score.quantize(Decimal('0.1'),rounding=ROUND_HALF_UP))
def ema(values, n):
    if len(values)<n: return None
    result=mean(values[:n]); alpha=2/(n+1)
    for v in values[n:]: result=v*alpha+result*(1-alpha)
    return result
def relative_to_benchmark(theme_return, benchmark_return):
    if not finite(theme_return) or not finite(benchmark_return): return None
    denom=1+benchmark_return/100
    if denom<=0:return None
    return 100*((1+theme_return/100)/denom-1)
def concentration_quality(values):
    gains=[v for v in values if finite(v) and v>0]
    if len(gains)<2:return 0.0
    total=sum(gains)
    if total<=0:return 0.0
    shares=[v/total for v in gains]
    hhi=sum(s*s for s in shares); floor=1/len(shares)
    return rnd(clamp(100*(1-hhi)/(1-floor)),1)

def bar_date(bar, market):
    return datetime.fromtimestamp(bar['t'], timezone.utc).astimezone(ZoneInfo('Asia/Tokyo' if market=='JP' else 'America/New_York')).date()

def valid_bars(doc, market, collected_at, symbol=""):
    overnight=symbol in {"TVC:US10Y","TVC:US02Y","TVC:DXY","TVC:USOIL","OANDA:XAUUSD","FX:USDJPY"}
    crypto=symbol.startswith("CRYPTO:")
    if not doc.get('success'): return []
    result=[]; seen=set()
    for b in sorted(doc.get('bars', []), key=lambda b:b['t']):
        if not finite(b.get('t')) or b['t'] in seen: raise ValueError('Invalid or duplicate bar timestamp')
        seen.add(b['t'])
        if any(not finite(b.get(k)) or b[k]<=0 for k in ['o','h','l','c']): raise ValueError('Invalid OHLC')
        if b['h']<max(b['o'],b['c'],b['l']) or b['l']>min(b['o'],b['c'],b['h']): raise ValueError('Inconsistent OHLC')
        if b.get('v') is not None and (not finite(b['v']) or b['v']<0): raise ValueError('Invalid volume')
        date=bar_date(b, market)
        if overnight and datetime.fromtimestamp(b['t'],timezone.utc).astimezone(ZoneInfo('America/New_York')).hour>=17: date+=timedelta(days=1)
        if crypto:date=datetime.fromtimestamp(b['t'],timezone.utc).date()
        zone=ZoneInfo('Asia/Tokyo' if market=='JP' else 'America/New_York')
        close=datetime.combine(date,time(15,30) if market=='JP' else time(17) if overnight else time(16),zone)+timedelta(minutes=30)
        if crypto:close=datetime.combine(date+timedelta(days=1),time(0),timezone.utc)+timedelta(minutes=15)
        if close>collected_at: continue
        result.append({**b,'date':date.isoformat()})
    return result

def percentile_map(values):
    ordered=sorted((v,k) for k,v in values.items() if finite(v)); n=len(ordered)
    result={}
    for v,k in ordered:
        indices=[i for i,(other,_) in enumerate(ordered) if other==v]
        result[k]=rnd(1+98*mean(indices)/(n-1),1) if n>1 else None
    return result

def relative_return(bars, benchmark, lookback):
    if len(bars)<=lookback: return None
    prices={b['date']:b['c'] for b in benchmark}
    start,end=bars[-lookback-1],bars[-1]
    if start['date'] not in prices or end['date'] not in prices: return None
    return 100*((end['c']/start['c'])/(prices[end['date']]/prices[start['date']])-1)

def metrics(bars, benchmark, asof):
    b=[x for x in bars if x['date']<=asof]
    if not b: return None
    prices=[x['c'] for x in b]; p=prices[-1]; last=b[-1]; current=last['date']==asof
    q={'price':p,'asOf':last['date'],'bars':len(b),'current':current,'source':'TradingView / split-adjusted OHLCV'}
    for name,n in [('return1D',1),('return5D',5),('return1W',5),('return1M',21)]: q[name]=rnd(100*(p/prices[-n-1]-1)) if len(b)>n else None
    day=datetime.fromisoformat(asof).date()
    if day.weekday()==4:
        week_start=(day-timedelta(days=day.weekday())).isoformat()
        previous_week=[x for x in b if x['date']<week_start]
        q['return1W']=rnd(100*(p/previous_week[-1]['c']-1)) if previous_week else None
    q['ma20']=rnd(mean(prices[-20:])) if len(b)>=20 else None
    for n in [21,50,150,200]:
        q['ma'+str(n)]=rnd(mean(prices[-n:])) if len(b)>=n else None
        prev=mean(prices[-n-5:-5]) if len(b)>=n+5 else None
        q['slope'+str(n)]=rnd(100*(q['ma'+str(n)]/prev-1)) if prev else None
    q['ema21']=rnd(ema(prices,21))
    q['volume']=last.get('v'); avg=mean([x.get('v') for x in b[-51:-1]]) if len(b)>=51 else None
    q['relativeVolume']=rnd(last.get('v')/avg) if finite(last.get('v')) and avg else None
    q['turnover']=rnd(p*last['v']) if finite(last.get('v')) else None
    q['dollarVolume']=q['turnover'] if benchmark[0].get('market')=='US' else None
    q['currency']='JPY' if benchmark[0].get('market')=='JP' else 'USD'
    q['above20']=p>q['ma20'] if finite(q['ma20']) else None
    q['above50']=p>q['ma50'] if finite(q['ma50']) else None
    q['above200']=p>q['ma200'] if finite(q['ma200']) else None
    q['high52']=max(x['h'] for x in b[-252:]) if len(b)>=252 else None
    q['low52']=min(x['l'] for x in b[-252:]) if len(b)>=252 else None
    q['rsRaw']=sum(relative_return(b,benchmark,n)*w for n,w in [(63,.4),(126,.2),(189,.2),(252,.2)]) if len(b)>=MIN_BARS and all(finite(relative_return(b,benchmark,n)) for n in [63,126,189,252]) and current else None
    q['rsLine']=relative_return(b,benchmark,63)
    ad=[(x,y) for x,y in zip(b[-26:-1],b[-25:]) if finite(x.get('v')) and finite(y.get('v'))]
    q['accumulationDays']=sum(y['c']>=x['c']*1.002 and y['v']>x['v'] for x,y in ad) if len(ad)==25 else None
    q['distributionDays']=sum(y['c']<=x['c']*.998 and y['v']>x['v'] for x,y in ad) if len(ad)==25 else None
    week={}
    for x in b:
        d=datetime.fromisoformat(x['date']).date()
        friday=d+timedelta(days=4-d.weekday())
        if friday.isoformat()<=asof: week[d.isocalendar()[:2]]=x['c']
    q['ma40Week']=rnd(mean(list(week.values())[-40:])) if len(week)>=40 else None
    q['salesGrowth']=None;q['epsGrowth']=None
    q['setup']=None;q['setupReady']=False;q['entry']=None;q['stop']=None;q['pivotDistancePct']=None;q['extensionPct']=None
    q['stage']='要確認';q['stageReason']='データ不足またはTrend Template未通過'
    q['templateChecks']={}
    if len(b)>=MIN_BARS:
        previous200=mean(prices[-221:-21])
        q['templateChecks']={'priceAbove50':p>q['ma50'],'priceAbove150':p>q['ma150'],'priceAbove200':p>q['ma200'],'ma50Above150':q['ma50']>q['ma150'],'ma150Above200':q['ma150']>q['ma200'],'ma200Rising21':q['ma200']>previous200,'above52Low30':p>=1.3*q['low52'],'within52High25':p>=.75*q['high52']}
    q['structure']='HH / HL' if len(b)>=40 and max(x['h'] for x in b[-20:])>max(x['h'] for x in b[-40:-20]) and min(x['l'] for x in b[-20:])>min(x['l'] for x in b[-40:-20]) else 'Mixed / 要確認'
    return q

def pattern(q,bars):
    if q['stage']!='Stage 2' or len(bars)<65: return
    prior=bars[-64:-1]; pivot=max(x['h'] for x in prior)
    base_range=100*(pivot/min(x['l'] for x in prior)-1)
    tight=100*(max(x['h'] for x in bars[-5:])/min(x['l'] for x in bars[-5:])-1)
    distance=100*(q['price']/pivot-1)
    label=None
    if base_range<=35 and tight<=8 and -8<=distance<=10: label='Base Breakout'
    elif finite(q['ema21']) and q['ema21']*.98<=q['price']<=q['ema21']*1.03 and q['price']>q['ma50'] and q['slope50']>0 and q['relativeVolume'] is not None and q['relativeVolume']<=1:
        label='Pullback / Retest';pivot=max(x['h'] for x in bars[-4:-1]);distance=100*(q['price']/pivot-1)
    if not label:return
    entry=pivot*1.001;stop=min(x['l'] for x in bars[-10:]);risk=100*(1-stop/entry)
    q.update(setup=label,setupOrigin='rule-candidate / manual chart review required',entry=rnd(entry),stop=rnd(stop),pivotDistancePct=rnd(100*(entry/q['price']-1)),extensionPct=rnd(max(0,100*(q['price']/entry-1))))
    q['setupReady']=bool(-5<=distance<=3 and 0<risk<=8 and finite(q['relativeVolume']) and (q['price']<entry and q['relativeVolume']<=.8 or q['price']>=entry and q['relativeVolume']>=1.5))

def immutable(path,data):
    text=json.dumps(data,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n'
    if path.exists() and path.read_text()!=text:raise ValueError(f'Immutable snapshot conflict: {path}')
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)

def build(input_path, activate=False):
    bundle=json.loads(Path(input_path).read_text()); collected_at=datetime.fromisoformat(bundle['fetchedAt'].replace('Z','+00:00'))
    config=json.loads((ROOT/'config/versions'/f'{VERSION}.json').read_text())
    cat=json.loads((ROOT/'data/theme-catalog.json').read_text())
    extras={'US':[('us-energy','Energy',['NYSE:XOM','NYSE:CVX']),('us-oil-services','Oil Services',['NYSE:SLB','NYSE:HAL']),('us-gold','Gold Miners',['NYSE:NEM','NYSE:AEM']),('us-utilities','Utilities',['NYSE:NEE','NYSE:DUK'])],'JP':[('jp-energy','エネルギー・石油',['TSE:1605','TSE:1662']),('jp-gold','金・貴金属',['TSE:5713','TSE:5711']),('jp-utilities','電力・ユーティリティ',['TSE:9503','TSE:9502'])]}
    docs=bundle['documents']; allbars={}; errors={}
    for symbol,doc in docs.items():
        m='JP' if symbol.startswith(('TSE:','TVC:NI225')) else 'US'
        try:allbars[symbol]=valid_bars(doc,m,collected_at,symbol)
        except ValueError as e:errors[symbol]=str(e);allbars[symbol]=[]
        if not allbars[symbol]:errors[symbol]=errors.get(symbol,doc.get('error','No completed bars'))
    benchmarks={'US':allbars.get('SP:SPX',[]),'JP':allbars.get('TVC:NI225',[])}
    if not all(benchmarks.values()):raise ValueError('Both market benchmarks are required')
    short_benchmarks={'US':benchmarks['US'],'JP':allbars.get('TSE:TOPIX',[]) or benchmarks['JP']}
    short_benchmark_symbols={'US':'SP:SPX','JP':'TSE:TOPIX' if allbars.get('TSE:TOPIX') else 'TVC:NI225'}
    for m in benchmarks:
        for b in benchmarks[m]:b['market']=m
    common_dates=sorted(set(b['date'] for b in benchmarks['US'])&set(b['date'] for b in benchmarks['JP']))
    asof=common_dates[-1]
    # Latest completed calendar week. Friday holidays use the last observed bar in that week.
    date=datetime.fromisoformat(asof).date(); friday=date-timedelta(days=(date.weekday()-4)%7)
    weekly_date=max(d for d in common_dates if d<=friday.isoformat())
    assets={'US':[('spx','S&P 500','SP:SPX','EQUITY'),('ndx','NASDAQ 100','NASDAQ:NDX','EQUITY'),('sox','SOX','NASDAQ:SOX','EQUITY'),('rut','Russell 2000','TVC:RUT','EQUITY'),('fang','FANG+','ICEUS:NYFANG','EQUITY')],'JP':[('nikkei','日経225','TVC:NI225','EQUITY'),('topix','TOPIX','TSE:TOPIX','EQUITY'),('growth','グロース250','TSE:MOS','EQUITY'),('usdJPY','USD / JPY','FX:USDJPY','RATES / FX')]}
    cross=[('us10y','US 10Y Yield','TVC:US10Y','RATES / FX'),('us2y','US 2Y Yield','TVC:US02Y','RATES / FX'),('dxy','DXY','TVC:DXY','RATES / FX'),('wti','WTI Crude Oil','TVC:USOIL','CROSS ASSET'),('gold','Gold','OANDA:XAUUSD','CROSS ASSET'),('btc','BTC','CRYPTO:BTCUSD','CROSS ASSET'),('vix','VIX','TVC:VIX','CROSS ASSET')]
    evaluated={}
    for market in ['US','JP']:
        themes=cat['markets'][market]['themes']+[{'id':tid,'name':name,'symbols':symbols,'catalogOrigin':'research-extension'} for tid,name,symbols in extras[market]]
        symbols=list(dict.fromkeys(s for t in themes for s in t['symbols']))
        def evaluate_date(target, weekly_eval=False):
            qs={s:metrics(allbars.get(s,[]),benchmarks[market],target) for s in symbols if s.startswith(('TSE:',) if market=='JP' else ('NASDAQ:','NYSE:','AMEX:'))}
            rs=percentile_map({s:q['rsRaw'] for s,q in qs.items() if q})
            for symbol,q in qs.items():
                if not q:continue
                symbol_bars=[b for b in allbars.get(symbol,[]) if b['date']<=target]
                q['dailyRelative1D']=rnd(relative_return(symbol_bars,short_benchmarks[market],1))
                q['dailyRelative5D']=rnd(relative_return(symbol_bars,short_benchmarks[market],5))
                if weekly_eval:
                    day=datetime.fromisoformat(target).date(); monday=(day-timedelta(days=day.weekday())).isoformat()
                    previous=[b for b in allbars[symbol] if b['date']<monday]
                    q['return1W']=rnd(100*(q['price']/previous[-1]['c']-1)) if previous else None
                q['rs']=rs.get(symbol);q['templateChecks']['rsUniverse70']=finite(q['rs']) and q['rs']>=70
                if q['current'] and len(q['templateChecks'])==9 and all(q['templateChecks'].values()):q['stage']='Stage 2';q['stageReason']='Trend Template proxy / watchlist RS, not IBD RS'
                pattern(q,[b for b in allbars[symbol] if b['date']<=target])
            result=[]
            for t in themes:
                valid=[qs[s] for s in t['symbols'] if qs.get(s) and qs[s]['current'] and finite(qs[s].get('rs'))]
                coverage=len(valid)/len(t['symbols']); eligible=len(valid)>=2 and coverage>=.8
                rvol_valid=[q for q in valid if finite(q.get('relativeVolume'))]
                stats={
                    'above20':rnd(100*sum(q['above20'] for q in valid)/len(valid),1) if valid else None,
                    'above50':rnd(100*sum(q['above50'] for q in valid)/len(valid),1) if valid else None,
                    'above200':rnd(100*sum(q['above200'] for q in valid)/len(valid),1) if valid else None,
                    'advancingPct':rnd(100*sum(q['return1D']>0 for q in valid)/len(valid),1) if valid else None,
                    'volumeParticipation':rnd(100*sum(q['return1D']>0 and q['relativeVolume']>=1 for q in rvol_valid)/len(rvol_valid),1) if rvol_valid else None,
                    'stage2Ratio':rnd(100*sum(q['stage']=='Stage 2' for q in valid)/len(valid),1) if valid else None
                }
                for key in ['return1D','return5D','return1W','return1M','relativeVolume','accumulationDays','distributionDays','rs','dailyRelative1D','dailyRelative5D']:
                    label={'rs':'relativeStrength','dailyRelative1D':'benchmarkRelative1D','dailyRelative5D':'benchmarkRelative5D'}.get(key,key)
                    stats[label]=rnd(mean([q[key] for q in valid]),1)
                stats.update(setupCount=sum(bool(q['setup']) for q in valid),setupReady=sum(q['setupReady'] for q in valid),extensionPct=rnd(mean([q['extensionPct'] for q in valid if finite(q['extensionPct'])])),breakouts=None,failedBreakouts=None,followThroughPct=None,coveragePct=rnd(coverage*100,1),validMembers=len(valid),totalMembers=len(t['symbols']),minimumMembers=2,rankEligible=eligible)
                stocks=[]
                for symbol in t['symbols']:
                    q=qs.get(symbol)
                    if q is None:q={'price':None,'stage':'未取得','rs':None,'setup':None,'setupReady':False,'entry':None,'stop':None,'current':False,'asOf':None,'templateChecks':{},'currency':'JPY' if market=='JP' else 'USD'}
                    usable=q.get('current') and finite(q.get('rs'))
                    liquidity=clamp(25*math.log10(max(1,(q.get('turnover') or 0)/(1e8 if market=='JP' else 1e6)))) if q.get('turnover') else None
                    components={'rs':q.get('rs'),'trend':100*sum(q.get('templateChecks',{}).values())/9 if len(q.get('templateChecks',{}))==9 else None,'structure':clamp(100*(q.get('price') or 0)/q['high52']) if q.get('high52') else None,'liquidity':liquidity,'accumulation':clamp(50+5*(q['accumulationDays']-q['distributionDays'])) if finite(q.get('accumulationDays')) and finite(q.get('distributionDays')) else None}
                    stocks.append({'symbol':symbol,'quantitative':q,'scores':{'leader':weighted(components,config['leader']) if usable else None,'components':components},'dataQuality':{'usable':bool(usable),'reason':None if usable else errors.get(symbol,'Insufficient history / stale session / unsupported exchange')}})
                stocks.sort(key=lambda s:(-(s['scores']['leader'] if finite(s['scores']['leader']) else -1),s['symbol']))
                result.append({**t,'category':'Observed themes','quantitative':stats,'scores':{'leaderQuality':stocks[0]['scores']['leader'] if stocks else None},'stocks':stocks})
            short_raw={t['id']:mean([t['quantitative']['benchmarkRelative1D'],t['quantitative']['benchmarkRelative5D']]) for t in result if t['quantitative']['rankEligible']}
            short_strength=percentile_map(short_raw)
            for t in result:
                q=t['quantitative'];q['dailyAcceleration']=short_strength.get(t['id']);q['shortRelativeStrengthRaw']=short_raw.get(t['id'])
                q['dailyBreadth']=rnd(mean([q['advancingPct'],q['above20']]),1) if finite(q.get('advancingPct')) and finite(q.get('above20')) else None
                q['concentrationQuality']=concentration_quality([s['quantitative'].get('dailyRelative5D') for s in t['stocks'] if s['dataQuality']['usable']])
                daily={'relativeStrengthShort':q['dailyAcceleration'],'breadth':q['dailyBreadth'],'participation':q['volumeParticipation'],'leaderQuality':t['scores']['leaderQuality'],'concentrationQuality':q['concentrationQuality']}
                weekly={'relativeStrength':q['relativeStrength'],'trendBreadth':q['above200'],'trendQuality':q['stage2Ratio'],'actionability':clamp(q['setupReady']*25)}
                t['scores'].update(daily=weighted(daily,config['daily']) if q['rankEligible'] else None,weekly=weighted(weekly,config['weekly']) if q['rankEligible'] else None,dailyComponents=daily,weeklyComponents=weekly)
            for period in ['daily','weekly']:
                ranked=sorted([t for t in result if finite(t['scores'][period])],key=lambda t:(-t['scores'][period],t['id']))
                ranks={t['id']:i+1 for i,t in enumerate(ranked)}
                for t in result:t['quantitative'][period+'Rank']=ranks.get(t['id'])
            return result
        for target in set([asof,weekly_date]):
            current=evaluate_date(target,weekly_eval=target==weekly_date);bd=[b['date'] for b in benchmarks[market] if b['date']<=target]
            pasts={n:evaluate_date(bd[-n-1]) if len(bd)>n else [] for n in [5,15]}
            for t in current:
                q=t['quantitative'];old={n:next((p for p in rows if p['id']==t['id']),None) for n,rows in pasts.items()}
                def diff(key,n,score=False):
                    a=t['scores' if score else 'quantitative'].get(key);p=old[n];b=p['scores' if score else 'quantitative'].get(key) if p else None
                    return rnd(a-b,1) if finite(a) and finite(b) else None
                q.update(breadthDelta5=diff('above50',5),leaderRSDelta5=diff('leaderQuality',5,True),weeklyDelta5=diff('weekly',5,True),weeklyDelta3Weeks=diff('weekly',15,True),above50History=[old[5]['quantitative']['above50'] if old[5] else None,q['above50']],rsHistory=[old[5]['quantitative']['relativeStrength'] if old[5] else None,q['relativeStrength']])
            asset_rows=[]
            for aid,name,symbol,group in assets[market]+cross:
                bars=[b for b in allbars.get(symbol,[]) if b['date']<=target]
                m=metrics(bars,benchmarks[market],target)
                if not m:m={}
                row={**m,'id':aid,'name':name,'symbol':symbol,'group':group,'unit':'%' if aid in ['us10y','us2y'] else 'USD' if aid in ['gold','wti','btc'] else '','changeUnit':'bp' if aid in ['us10y','us2y'] else '%','maType':'SMA','source':'TradingView / observed'}
                for key,n in [('change1D',1),('change1W',7 if aid=='btc' else 5),('change1M',30 if aid=='btc' else 21)]: row[key]=rnd((bars[-1]['c']-bars[-n-1]['c'])*100) if aid in ['us10y','us2y'] and len(bars)>n else rnd(100*(bars[-1]['c']/bars[-n-1]['c']-1)) if aid=='btc' and len(bars)>n else m.get({'change1D':'return1D','change1W':'return1W','change1M':'return1M'}[key])
                if target==weekly_date and aid!='btc' and bars:
                    day=datetime.fromisoformat(target).date();monday=(day-timedelta(days=day.weekday())).isoformat();prev=[b for b in bars if b['date']<monday]
                    row['change1W']=rnd((bars[-1]['c']-prev[-1]['c'])*100 if aid in ['us10y','us2y'] else 100*(bars[-1]['c']/prev[-1]['c']-1)) if prev else None
                asset_rows.append(row)
            by={a['id']:a for a in asset_rows};a,b=by['us10y'],by['us2y']
            spread={'id':'spread','name':'10Y−2Y Spread','group':'RATES / FX','unit':'%','changeUnit':'bp','source':'Derived from observed yields'}
            for key in ['price','change1D','change1W','change1M','ma21','ma50','ma150','ma200']:spread[key]=rnd(a[key]-b[key],3) if finite(a.get(key)) and finite(b.get(key)) else None
            for key in ['slope21','slope50','slope150','slope200']:spread[key]=None
            asset_rows.append(spread)
            valid=[s['quantitative'] for t in current for s in t['stocks'] if s['dataQuality']['usable']]
            unique={s['symbol']:s['quantitative'] for t in current for s in t['stocks'] if s['dataQuality']['usable']}
            valid=list(unique.values())
            breadth={'universe':'Current theme watchlists + research extensions; not exchange-wide','validMembers':len(valid),'requestedMembers':len(symbols),'above50':rnd(100*sum(q['above50'] for q in valid)/len(valid),1),'above200':rnd(100*sum(q['above200'] for q in valid)/len(valid),1),'advancing':sum(q['return1D']>0 for q in valid),'declining':sum(q['return1D']<0 for q in valid)} if valid else {'validMembers':0}
            benchmark=metrics(benchmarks[market],benchmarks[market],target)
            trend=100*mean([int(benchmark['price']>benchmark['ma'+str(n)]) for n in [21,50,150,200]])
            institution=clamp(50+5*(benchmark['accumulationDays']-benchmark['distributionDays'])) if finite(benchmark['accumulationDays']) and finite(benchmark['distributionDays']) else None
            health={'trend':trend,'institutionalAction':institution,'breadth':breadth.get('above50'),'leadership':rnd(100*sum(q['stage']=='Stage 2' for q in valid)/len(valid),1) if valid else None,'breakoutQuality':None}
            # Index volume is unavailable in Japan: use a documented neutral-free three-component model.
            weights=config['marketHealth'] if finite(institution) else config['marketHealthWithoutVolume']
            market_data={'source':cat['markets'][market]['source'],'asOf':target,'assets':asset_rows,'marketQuantitative':{'assets':asset_rows,'breadth':breadth,'leadership':{'stage2Ratio':health['leadership'],'definition':'Trend Template proxy'},'breakoutQuality':{'status':'Not implemented'}},'scores':{'marketHealth':weighted(health,weights),'marketComponents':health},'marketHealthWeights':weights,'themes':current,'ibdReference':{'available':False,'reason':'Not connected'},'dataQuality':{'errors':{s:errors.get(s,'Unsupported exchange') for s in symbols if s in errors or s.startswith('OMXSTO:')},'sourceAsOf':target,'benchmark':'SP:SPX' if market=='US' else 'TVC:NI225','dailyBenchmark':short_benchmark_symbols[market]}}
            evaluated[(market,target)]=market_data
    manifest_path=ROOT/'data/live/latest.json'
    manifest=json.loads(manifest_path.read_text()) if manifest_path.exists() else {'schemaVersion':2,'mode':'live','daily':[],'weekly':[]}
    for period,target in [('daily',asof),('weekly',weekly_date)]:
        iso=datetime.fromisoformat(target).date().isocalendar();key=target if period=='daily' else f'{iso.year}-W{iso.week:02d}'
        path=f'live/{period}/{key}.json';rawpath=f'raw/live/{period}-{key}.json'
        data={'schemaVersion':2,'mode':'live','period':period,'asOf':target,'evaluationVersion':VERSION,'generatedAt':bundle['fetchedAt'],'provenance':'observed-technical-snapshot' if period=='daily' else 'retrospective-quantitative-import','source':'TradingView MCP / completed split-adjusted bars','markets':{m:evaluated[(m,target)] for m in ['US','JP']}}
        immutable(ROOT/'data'/path,data)
        immutable(ROOT/'data'/rawpath,{'schemaVersion':2,'mode':'live','asOf':target,'timestamp':bundle['fetchedAt'],'sourceRef':str(input_path),'markets':{m:data['markets'][m]['marketQuantitative'] for m in ['US','JP']}})
        entry={'key':key,'asOf':target,'path':path,'rawPath':rawpath,'analysisPath':None,'provenance':data['provenance']}
        if not any(e['key']==key for e in manifest[period]):manifest[period].append(entry)
        manifest[period].sort(key=lambda e:e['asOf'])
    manifest.update(lastSuccessfulUpdate=bundle['fetchedAt'],expectedNextUpdate=(collected_at+timedelta(hours=36)).isoformat(),sourceNotice='Delayed OHLCV, split adjusted only; daily session close +30 minutes; no pre/post market. No dividend total return.',notes=['US / JP common completed session date','RS percentile is within current watchlist universe, not IBD','Daily v1 uses 1D/5D benchmark-relative strength + breadth + volume participation + leader + concentration quality','Weekly first import is retrospective quantitative, not prior saved prediction','Manual connector collection; scheduled collection not configured'])
    manifest_path.parent.mkdir(parents=True,exist_ok=True);manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    if activate:(ROOT/'data/latest.json').write_text(json.dumps({'schemaVersion':2,'mode':'live','manifestPath':'live/latest.json'})+'\n')
    print(json.dumps({'asOf':asof,'weeklyAsOf':weekly_date,'sourceSymbols':len(docs),'errors':errors,'markets':{m:{'themes':len(evaluated[(m,asof)]['themes']),'members':evaluated[(m,asof)]['marketQuantitative']['breadth'].get('validMembers')} for m in ['US','JP']}},ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--activate',action='store_true');args=p.parse_args();build(args.input,args.activate)
