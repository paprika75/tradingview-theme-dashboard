"""Calculate draft levels from chart-reviewer-selected structural windows.

Window selection is discretionary. Output is deliberately unconfirmed and cannot
be submitted as a formal promotion until a reviewer verifies every requirement.
"""
import argparse
import json
from datetime import date
from pathlib import Path
from setup_journey import PATTERN_CHECKS, positive, risk_pct


def propose(doc):
    asof = doc['asOf']
    date.fromisoformat(asof)
    kind = doc['setup_type']
    if kind not in PATTERN_CHECKS:
        raise ValueError('VCP / CWH / Base Breakout only')
    bars = doc['completedBars']
    if not bars or any(b['date']>asof or not all(positive(b.get(k)) for k in ['h','l','c']) or b['l']>b['h'] for b in bars):
        raise ValueError('Dated completed bars with valid positive prices are required')
    levels = {}
    for key in ['pivotWindow','stopWindow']:
        window = doc[key]
        start,end = window['start'],window['end']
        if start>end or end>asof or not window.get('basis'):
            raise ValueError('A dated structural window and its chart basis are required')
        selected = [b for b in bars if start<=b['date']<=end]
        if not selected:
            raise ValueError('No bars in structural window')
        levels[key] = max(b['h'] for b in selected) if key=='pivotWindow' else min(b['l'] for b in selected)
    pivot,stop = levels['pivotWindow'],levels['stopWindow']
    entry = pivot*(1+doc.get('entryBufferPct',0.1)/100)
    if entry < pivot or risk_pct(entry,stop) is None:
        raise ValueError('Invalid Standard Entry / structural Stop')
    price = max(bars,key=lambda b:b['date'])['c']
    extension = 100*(price/pivot-1)
    return {'schemaVersion':1,'asOf':asof,'symbol':doc['symbol'],'setup_type':kind,
            'setupConfirmed':False,'lifecycleConfirmed':False,'source':'STRUCTURAL_WINDOW_PROPOSAL',
            'pivot':pivot,'pivotBasis':doc['pivotWindow'],'entry':round(entry,6),'stop':stop,
            'stopBasis':doc['stopWindow'],'riskPct':risk_pct(entry,stop),'extensionPct':round(extension,4),
            'extendedCandidate':extension>=doc.get('extendedPct',10),
            'patternChecks':dict.fromkeys(PATTERN_CHECKS[kind],False),
            'nextCheck':'窓の選択・型・正式Pivot・Stopを手動確認。無効なら昇格せず再形成待ち',
            'watchlistsChanged':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(propose(json.loads(args.input.read_text())),ensure_ascii=False,indent=2))
