"""Narration provider failure must produce a truthful full-film fallback or fail."""
import asyncio
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('peace_long',ROOT/'peace_av/render_long.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
ENTRIES=[{'english':'First section.'},{'english':'Second section.'}]

class ProviderFailure(RuntimeError):pass

class NarrationTests(unittest.TestCase):
    def audio(self,text,path,engine,voice,rate):path.write_bytes(b'x'*1200)

    def test_success_keeps_online_voice_for_all_scenes(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(m,'speech',side_effect=self.audio) as synth, patch.object(m,'duration',return_value=1):
            paths,meta=m.prepare_narration(ENTRIES,Path(temp),'auto','voice','-13%')
            self.assertEqual(meta,dict(requested_engine='auto',engine='edge',voice='voice',fallback=None))
            self.assertEqual([p.suffix for p in paths],['.mp3','.mp3'])
            self.assertEqual([c.args[2] for c in synth.call_args_list],['edge','edge'])

    def test_partial_online_batch_is_removed_and_entire_film_rebuilt_offline(self):
        calls=[]
        def synth(text,path,engine,voice,rate):
            calls.append((text,engine));path.write_bytes(b'x'*1200)
            if engine=='edge' and text==ENTRIES[1]['english']:
                raise ProviderFailure('403 https://provider/?token=DO_NOT_LOG')
        log=io.StringIO()
        with tempfile.TemporaryDirectory() as temp, patch.object(m,'speech',side_effect=synth), patch.object(m,'duration',return_value=1), contextlib.redirect_stdout(log):
            paths,meta=m.prepare_narration(ENTRIES,Path(temp),'auto','voice','-13%')
            self.assertFalse(list(Path(temp).glob('*.mp3')))
            self.assertTrue(all(p.suffix=='.wav' and p.exists() for p in paths))
            self.assertEqual(calls,[(e['english'],engine) for engine in ('edge','espeak') for e in ENTRIES])
            self.assertEqual(meta['engine'],'espeak');self.assertEqual(meta['voice'],'espeak en-us')
            self.assertEqual(meta['fallback']['error_type'],'ProviderFailure')
            self.assertNotIn('DO_NOT_LOG',log.getvalue())

    def test_strict_online_mode_does_not_switch_engine(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(m,'speech',side_effect=ProviderFailure('blocked')) as synth:
            with self.assertRaises(ProviderFailure):m.prepare_narration(ENTRIES,Path(temp),'edge','voice','-13%')
            self.assertEqual(synth.call_count,1)

    def test_failed_offline_fallback_still_fails_and_cleans_up(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(m,'speech',side_effect=ProviderFailure('failed')), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(ProviderFailure):m.prepare_narration(ENTRIES,Path(temp),'auto','voice','-13%')
            self.assertFalse(list(Path(temp).glob('speech_*')))

    def test_invalid_online_audio_triggers_valid_offline_fallback(self):
        def synth(text,path,engine,voice,rate):path.write_bytes(b'' if engine=='edge' else b'x'*1200)
        with tempfile.TemporaryDirectory() as temp, patch.object(m,'speech',side_effect=synth), patch.object(m,'duration',return_value=1), contextlib.redirect_stdout(io.StringIO()):
            paths,meta=m.prepare_narration(ENTRIES,Path(temp),'auto','voice','-13%')
            self.assertEqual(meta['engine'],'espeak');self.assertTrue(all(p.stat().st_size>1000 for p in paths))

    def test_provider_retries_are_bounded(self):
        async def fail(*a):raise ProviderFailure('blocked')
        with tempfile.TemporaryDirectory() as temp, patch.object(m,'edge_speech',side_effect=fail) as provider, patch.object(m.time,'sleep') as delay:
            with self.assertRaises(ProviderFailure):m.speech('text',Path(temp)/'a.mp3','edge','voice','-13%')
            self.assertEqual(provider.call_count,3)
            self.assertEqual([c.args[0] for c in delay.call_args_list],[1,2])

    @unittest.skipUnless(shutil.which('espeak') and shutil.which('ffprobe'),'requires installed media tools')
    def test_real_offline_speech_can_be_decoded(self):
        with tempfile.TemporaryDirectory() as temp:
            paths,meta=m.prepare_narration(ENTRIES,Path(temp),'espeak','unused','-13%')
            self.assertEqual(meta['engine'],'espeak');self.assertTrue(all(m.duration(p)>0 for p in paths))

if __name__=='__main__':unittest.main()
