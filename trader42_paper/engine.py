#!/usr/bin/env python3
"""Trader_42 PAPER-ONLY deterministic simulator. NO broker, network, or orders."""
import argparse
from dataclasses import dataclass,asdict
from decimal import Decimal,InvalidOperation
import json

def D(v):
    try:
        d=Decimal(str(v))
        if not d.is_finite():raise ValueError("nonfinite amount")
        return d
    except (InvalidOperation,TypeError) as e:raise ValueError("invalid decimal") from e

@dataclass(frozen=True)
class Limits:
    initial_cash:str="10000"
    max_notional:str="500"
    max_position_units:str="10"
    max_daily_loss:str="100"
    fee_rate:str="0.001"

class PaperEngine:
    """BUY/SELL are simulated book entries only; no real trading methods exist."""
    def __init__(self,limits=Limits()):
        self.limits=limits
        self.cash=D(limits.initial_cash)
        self.initial=self.cash
        self.units=D(0)
        self.avg_cost=D(0)
        self.realized=D(0)
        self.fees=D(0)
        self.events=[]
        self.halted=False
        self._validate_limits()

    def _validate_limits(self):
        l=self.limits
        if not (D(l.initial_cash)>0 and D(l.max_notional)>0 and
                D(l.max_position_units)>0 and D(l.max_daily_loss)>0 and
                D(l.fee_rate)>=0 and D(l.fee_rate)<1):
            raise ValueError("invalid paper limits")

    def _record(self,kind,price,qty,reason):
        ev={"mode":"PAPER_ONLY","kind":kind,"price":str(price),"qty":str(qty),
            "cash":str(self.cash),"units":str(self.units),"realized":str(self.realized),
            "fees":str(self.fees),"reason":reason}
        self.events.append(ev)
        return ev

    def trade(self,kind,price,qty):
        if kind not in ("BUY","SELL"):raise ValueError("unknown paper side")
        price,qty=D(price),D(qty)
        if price<=0 or qty<=0:raise ValueError("positive price and qty required")
        if self.halted:raise ValueError("PAPER_HALT_DAILY_LOSS")
        notional=price*qty
        if notional>D(self.limits.max_notional):raise ValueError("PAPER_LIMIT_ORDER_NOTIONAL")
        fee=notional*D(self.limits.fee_rate)
        if kind=="BUY":
            if self.units+qty>D(self.limits.max_position_units):raise ValueError("PAPER_LIMIT_POSITION")
            if notional+fee>self.cash:raise ValueError("PAPER_LIMIT_CASH")
            total_cost=self.avg_cost*self.units+notional+fee
            self.cash-=notional+fee
            self.units+=qty
            self.avg_cost=total_cost/self.units
        else:
            if qty>self.units:raise ValueError("PAPER_NO_SHORT_SELL")
            self.cash+=notional-fee
            self.realized+=(price-self.avg_cost)*qty-fee
            self.units-=qty
            if self.units==0:self.avg_cost=D(0)
        self.fees+=fee
        return self._record(kind,price,qty,"SIMULATED_FILL_NOT_EXCHANGE_EXECUTION")

    def mark(self,price):
        price=D(price)
        if price<=0:raise ValueError("positive mark required")
        equity=self.cash+self.units*price
        pnl=equity-self.initial
        if pnl<=-D(self.limits.max_daily_loss):self.halted=True
        return {"mode":"PAPER_ONLY","equity":str(equity),"pnl":str(pnl),
                "halted":self.halted,"units":str(self.units),
                "orders_submitted":0,"real_funds_used":False}

def run(spec):
    if type(spec) is not dict or set(spec)-{"limits","actions"}:raise ValueError("invalid input fields")
    lim=spec.get("limits",{})
    if type(lim) is not dict or set(lim)-set(Limits.__dataclass_fields__):raise ValueError("invalid limits")
    actions=spec.get("actions",[])
    if type(actions) is not list or len(actions)>1000:raise ValueError("invalid actions")
    engine=PaperEngine(Limits(**lim))
    marks=[]
    for action in actions:
        if type(action) is not dict:raise ValueError("invalid action")
        if action.get("kind")=="MARK" and set(action)=={"kind","price"}:
            marks.append(engine.mark(action["price"]))
        elif action.get("kind") in ("BUY","SELL") and set(action)=={"kind","price","qty"}:
            engine.trade(action["kind"],action["price"],action["qty"])
        else:raise ValueError("invalid action fields")
    return {"protocol":"TRADER42-PAPER/1","orders_submitted":0,"broker_connected":False,
            "real_funds_used":False,"events":engine.events,"marks":marks,
            "halted":engine.halted}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True,help="local JSON simulation file")
    a=p.parse_args()
    with open(a.input,encoding="utf-8") as f:spec=json.load(f)
    print(json.dumps(run(spec),ensure_ascii=False,sort_keys=True,indent=2))

if __name__=="__main__":main()
