"""Offline historical replay of user-provided price and signals; no network or broker."""
import csv, json, sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

def dec(s):
    try:
        v=Decimal(str(s))
        if not v.is_finite(): raise ValueError('nonfinite')
        return v
    except InvalidOperation as e: raise ValueError('invalid number') from e

def replay(path):
    path=Path(path)
    if path.is_symlink() or path.stat().st_size>2_000_000: raise ValueError('unsafe file')
    cash=Decimal('10000'); qty=Decimal(0); fee_rate=Decimal('0.001')
    events=[]; previous=None; bars=0; halted=False
    with path.open(newline='',encoding='utf-8-sig') as f:
        reader=csv.DictReader(f)
        if reader.fieldnames!=['timestamp','price','signal','qty']: raise ValueError('invalid header')
        for row in reader:
            bars+=1
            if bars>10000 or None in row: raise ValueError('invalid row count or columns')
            t=row['timestamp']; price=dec(row['price']); signal=row['signal']
            if not t or (previous is not None and t<=previous): raise ValueError('timestamps out of order')
            previous=t
            if price<=0 or signal not in ('BUY','SELL','HOLD'): raise ValueError('invalid price or signal')
            amount=dec(row['qty'] or '0')
            if amount<0 or (signal=='HOLD' and amount!=0): raise ValueError('invalid quantity')
            if signal!='HOLD':
                if amount<=0 or halted: raise ValueError('invalid or halted order')
                notional=amount*price; fee=notional*fee_rate
                if notional>500: raise ValueError('order limit')
                if signal=='BUY':
                    if qty+amount>10 or cash<notional+fee: raise ValueError('position or cash limit')
                    cash-=notional+fee;qty+=amount
                else:
                    if qty<amount: raise ValueError('no short selling')
                    cash+=notional-fee;qty-=amount
                events.append({'timestamp':t,'side':signal,'price':str(price),'qty':str(amount),'simulated_only':True})
            equity=cash+qty*price
            if equity<=Decimal('9900'): halted=True
    if not bars: raise ValueError('empty input')
    return {'mode':'PAPER_ONLY','bars':bars,'cash':str(cash),'units':str(qty),'equity':str(equity),'halted':halted,'fills':events,'real_orders':0,'broker_connected':False,'caveat':'No slippage, spread, or market impact modeled; not an execution-quality backtest.'}
if __name__=='__main__':
    print(json.dumps(replay(sys.argv[1]),indent=2))
