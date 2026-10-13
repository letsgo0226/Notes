"""Offline UNSD fixtures: coverage, provenance and fail-closed pagination."""
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from hsi_account_utm import sdg_state as mod

HERE = pathlib.Path(__file__).resolve().parent


def fixture():
    return {'geographies': [
        {'geoAreaCode':'4','geoAreaName':'Example Area A','type':'Country'},
        {'geoAreaCode':'8','geoAreaName':'Example Area B','type':'Country'},
        {'geoAreaCode':'1','geoAreaName':'Regional total','type':'Region'}],
        'series': {
            '16.1.1':[{'code':'VC_IHR_PSRC','description':'Homicide per 100,000'}],
            '16.1.2':[{'code':'VC_DTH_TOCV','description':'Conflict related deaths'}]},
        'pages':{
            'VC_IHR_PSRC':[{'totalPages':1,'data':[
                {'geoAreaCode':4,'timePeriodStart':2019,'value':'3.0','source':'Fixture','dimensions':{'SEX':'T'}},
                {'geoAreaCode':4,'timePeriodStart':2022,'value':'4.5','source':'Fixture','dimensions':{'SEX':'T'}},
                {'geoAreaCode':4,'timePeriodStart':2022,'value':'2','source':'Fixture','dimensions':{'SEX':'F'}},
                {'geoAreaCode':1,'timePeriodStart':2022,'value':'99','source':'Fixture'}]}],
            'VC_DTH_TOCV':[{'totalPages':1,'data':[
                {'geoAreaCode':4,'timePeriodStart':2020,'value':'0','source':'Fixture'}]}]}}


class SDGTMTests(unittest.TestCase):
    def test_e257_reversible_code_examples(self):
        self.assertEqual(mod.e257(b''),'0x1')
        self.assertEqual(mod.e257(b'A'),hex(257+66))

    def test_snapshots_keep_missingness_time_and_dimensions(self):
        r=mod.build_snapshot(fixture(),'2026-10-13T00:00:00+00:00')
        self.assertTrue(r['not_realtime'])
        self.assertFalse(r['live_deploy'])
        self.assertEqual(r['area_count'],3)
        self.assertEqual(r['country_typed_count'],2)
        self.assertEqual(r['observed_area_count'],2)
        byid={x['geography']['code']:x for x in r['states']}
        self.assertFalse(byid['8']['has_observations'])
        self.assertEqual(byid['1']['geography']['kind'],'unclassified_area')
        t=next(x for x in byid['4']['tracks'] if x['dimensions']=={'SEX':'T'})
        self.assertEqual((t['latest_period'],t['previous_period'],t['arithmetic_delta']),('2022','2019','1.5'))
        self.assertEqual(t['latest_observations'][0]['source'],'Fixture')

    def test_conflict_retained_not_averaged(self):
        p=fixture()
        p['pages']['VC_IHR_PSRC'][0]['data'].append({'geoAreaCode':4,'timePeriodStart':2022,'value':'4.6','source':'Other','dimensions':{'SEX':'T'}})
        state=mod.build_snapshot(p,'2026-10-13T00:00:00+00:00')
        country=next(x for x in state['states'] if x['geography']['code']=='4')
        row=next(x for x in country['tracks'] if x['dimensions']=={'SEX':'T'})
        self.assertTrue(row['conflicting_latest_observations'])
        self.assertEqual(len(row['latest_observations']),2)
        self.assertIsNone(row['arithmetic_delta'])

    def test_incomplete_pagination_rejected(self):
        p=fixture(); p['pages']['VC_IHR_PSRC'][0]['totalPages']=2
        with self.assertRaisesRegex(ValueError,'Partial pagination'):
            mod.build_snapshot(p,'2026-10-13T00:00:00+00:00')

    def test_cli_fixture_offline_no_api(self):
        with tempfile.TemporaryDirectory() as path:
            d=pathlib.Path(path); src=d/'fixture.json'; dest=d/'state.json'
            src.write_text(json.dumps(fixture()),encoding='utf-8')
            subprocess.run([sys.executable,str(HERE/'sdg_state.py'),
                            '--fixture',str(src),'--out',str(dest)],
                           check=True,timeout=7,capture_output=True)
            output=json.loads(dest.read_text(encoding='utf-8'))
            self.assertEqual(output['raw_observation_count'],5)
            self.assertTrue(output['fetched_at_utc'])
            self.assertFalse(output['autonomous_political_decisions'])

if __name__=='__main__':
    unittest.main()
