#!/usr/bin/env python3
"""UNSD SDG 16 public observation snapshots; no autonomous political actions."""
import argparse
import datetime as dt
import hashlib
import json
import re
import urllib.parse
import urllib.request
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

BASE = 'https://unstats.un.org/SDGAPI/v1/sdg/'
INDICATORS = ('16.1.1', '16.1.2')
PROTOCOL = 'HSI-SDG-TM-READONLY/1'


def canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')


def e257(data):
    n = 1
    for b in data:
        n = 257*n + b + 1
    return hex(n)


def fetch_json(endpoint, parameters=None):
    # Caller supplies only fixed endpoints / validated official series codes.
    url = BASE + endpoint + ('?' + urllib.parse.urlencode(parameters) if parameters else '')
    req = urllib.request.Request(url, headers={'Accept':'application/json','User-Agent':'HSI-SDG-TM-readonly/1'})
    with urllib.request.urlopen(req, timeout=25) as response:
        if response.geturl().split('?')[0].lower().startswith(BASE.lower()) is False:
            raise ValueError('Redirect outside official UNSD SDG API')
        raw = response.read(8_000_001)
        if len(raw) > 8_000_000:
            raise ValueError('UNSD response too large')
        return json.loads(raw)


def get_live():
    areas = fetch_json('GeoArea/List')
    series = {}
    pages = {}
    for ind in INDICATORS:
        desc = fetch_json('Indicator/' + ind + '/Series/List')
        if not isinstance(desc, list):
            raise ValueError('Unexpected series list for ' + ind)
        codes = sorted(set(row.get('code') for row in desc if isinstance(row, dict)
                           and isinstance(row.get('code'), str)
                           and re.fullmatch(r'[A-Z0-9_]{1,80}',row['code'])))
        if not codes or len(codes)>8:
            raise ValueError('No valid or too many series for '+ind)
        series[ind] = [{'code':c, 'description':next((row.get('description') for row in desc if row.get('code')==c),'')} for c in codes]
        for code in codes:
            pages[code] = []
            for n in range(1,31):
                record = fetch_json('Series/Data', {'seriesCode':code,'pageSize':400,'page':n})
                if not isinstance(record,dict) or not isinstance(record.get('data'),list):
                    raise ValueError('Unexpected UNSD series page '+code)
                pages[code].append(record)
                total=record.get('totalPages')
                if total is not None:
                    if type(total) is not int or total<1:
                        raise ValueError('Bad pagination '+code)
                    if n>=total: break
                elif len(record['data'])<400: break
            else:
                raise ValueError('Series exceeds 30 pages; do not treat as complete: '+code)
    return {'geographies':areas,'series':series,'pages':pages}


def decimal_value(s):
    try:
        d = Decimal(str(s))
        return d if d.is_finite() else None
    except (InvalidOperation, ValueError):
        return None


def build_snapshot(payload, fetched_at):
    areas = payload.get('geographies')
    if not isinstance(areas,list) or not areas:
        raise ValueError('Official geography list missing')
    known={}
    for row in areas:
        if not isinstance(row,dict): continue
        code=str(row.get('geoAreaCode',''))
        if not re.fullmatch(r'\d{1,3}', code): continue
        raw_type=str(row.get('type',''))
        # Never infer country-hood from numeric IDs alone; keep UNSD type verbatim.
        known[code]={'code':code,'name':str(row.get('geoAreaName','')),
                     'source_type':raw_type,
                     'kind':'country' if raw_type.strip().lower() in ('country','countries') else 'unclassified_area',
                     'code_e257':e257(code.encode('ascii'))}
    if not known: raise ValueError('No valid areas')
    defs = payload.get('series')
    pages = payload.get('pages')
    if not isinstance(defs,dict) or not isinstance(pages,dict):
        raise ValueError('Missing series definitions or observations')
    tracks=defaultdict(list)
    total=0
    for indicator in INDICATORS:
        rows=defs.get(indicator)
        if not isinstance(rows,list) or not rows or len(rows)>8:
            raise ValueError('Incomplete indicator series '+indicator)
        for entry in rows:
            code=entry.get('code') if isinstance(entry,dict) else None
            if not isinstance(code,str) or not re.fullmatch(r'[A-Z0-9_]{1,80}',code):
                raise ValueError('Invalid series code')
            chunks=pages.get(code)
            if not isinstance(chunks,list) or not chunks:
                raise ValueError('Missing pages '+code)
            for page_index,page in enumerate(chunks,1):
                if not isinstance(page,dict) or not isinstance(page.get('data'),list):
                    raise ValueError('Malformed data page')
                if page.get('totalPages') is not None and page_index==len(chunks) and page_index<page['totalPages']:
                    raise ValueError('Partial pagination '+code)
                for obs in page['data']:
                    if not isinstance(obs,dict): continue
                    geo=str(obs.get('geoAreaCode',''))
                    if geo not in known: continue
                    period=obs.get('timePeriodStart')
                    if not isinstance(period,(str,int)) or not re.fullmatch(r'\d{4}',str(period)): continue
                    dimensions=obs.get('dimensions') or {}
                    if not isinstance(dimensions,dict): continue
                    raw=obs.get('value')
                    if raw is None or str(raw).strip()=='': continue
                    record={'period':str(period),'value':str(raw),'value_type':str(obs.get('valueType') or ''),
                            'source':str(obs.get('source') or ''),
                            'time_detail':str(obs.get('time_detail') or ''),
                            'footnotes':obs.get('footnotes') if isinstance(obs.get('footnotes'),list) else [],
                            'dimensions':dimensions}
                    key=(geo,indicator,code,canonical(dimensions).decode('utf-8'))
                    tracks[key].append(record);total+=1
    states={code:dict(geography=meta,tracks=[]) for code,meta in known.items()}
    for (geo,ind,code,dimension_key),items in sorted(tracks.items()):
        latest_period=max(item['period'] for item in items)
        latest=[item for item in items if item['period']==latest_period]
        before=[item for item in items if item['period']<latest_period]
        prev_period=max((item['period'] for item in before),default=None)
        previous=[item for item in before if item['period']==prev_period]
        delta=None
        if len(latest)==1 and len(previous)==1:
            a,b=decimal_value(latest[0]['value']),decimal_value(previous[0]['value'])
            if a is not None and b is not None:
                delta=str(a-b)
        states[geo]['tracks'].append({'indicator':ind,'series':code,
            'dimensions':json.loads(dimension_key),'latest_period':latest_period,
            'latest_observations':latest,'previous_period':prev_period,
            'previous_observations':previous,'arithmetic_delta':delta,
            'conflicting_latest_observations':len(set(canonical(x) for x in latest))>1})
    values=[]
    for code in sorted(states,key=lambda s:int(s)):
        state=states[code]
        body={'geography':state['geography'],'tracks':state['tracks']}
        values.append({**body,'has_observations':bool(state['tracks']),
                       'state_sha256':hashlib.sha256(canonical(body)).hexdigest()})
    return {'protocol':PROTOCOL,'source':'United Nations Statistics Division SDG API',
            'official_api':BASE,'fetched_at_utc':fetched_at,
            'fetched_at_is_observation_time':False,
            'not_realtime':True,'indicators':list(INDICATORS),
            'area_count':len(values),'country_typed_count':sum(s['geography']['kind']=='country' for s in values),
            'observed_area_count':sum(s['has_observations'] for s in values),
            'raw_observation_count':total,
            'not_all_countries_guaranteed':True,'autonomous_political_decisions':False,
            'cross_repo_write':False,'live_deploy':False,'live_trading':False,
            'states':values}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--fixture',help='offline test source; no network calls')
    ap.add_argument('--out',required=True)
    a=ap.parse_args()
    data=json.loads(Path(a.fixture).read_text(encoding='utf-8')) if a.fixture else get_live()
    timestamp=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
    result=build_snapshot(data,timestamp)
    Path(a.out).write_bytes(canonical(result)+b'\n')
    print(json.dumps({'status':'READ_ONLY_SDG_SNAPSHOT','areas':result['area_count'],
                      'country_typed':result['country_typed_count'],
                      'areas_with_observations':result['observed_area_count'],
                      'observations':result['raw_observation_count'],
                      'output':a.out,'not_realtime':True}))


if __name__=='__main__':main()
