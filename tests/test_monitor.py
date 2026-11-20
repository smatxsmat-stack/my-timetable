import contextlib,io,json,shutil,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from sources import bus
from check_updates import run,validate_route,holiday_candidate
class MonitorTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)/'app';shutil.copytree(ROOT,self.root,ignore=shutil.ignore_patterns('dist','__pycache__','.git','reports'))
  shutil.copytree(ROOT/'tests/fixtures',self.root,dirs_exist_ok=True)
  self.fixtures=Path(self.tmp.name)/'fixtures';shutil.copytree(ROOT/'tests/fixtures/evidence',self.fixtures)
  shutil.copytree(ROOT/'evidence/fares',self.fixtures/'fares')
 def tearDown(self):self.tmp.cleanup()
 def go(self):
  with contextlib.redirect_stdout(io.StringIO()):return run(self.root,self.fixtures,'2026-11-16')
 def data(self):return json.loads((self.root/'data.json').read_text())
 def test_baseline(self):
  before=self.data();s=self.go();self.assertFalse(s['alerts']);self.assertEqual(before['routes'],self.data()['routes'])
 def test_verified_bus_time_change(self):
  p=self.fixtures/'bus63.html';p.write_text(p.read_text().replace('9:47&nbsp;','9:48&nbsp;'))
  s=self.go();self.assertFalse(s['alerts']);self.assertEqual(self.data()['routes']['sansai_gondo_bus']['times'][0][0],'09:48');self.assertIn('sansai_gondo_bus',s['updatedRoutes'])
 def test_unknown_bus_note_preserves_both_directions(self):
  before=self.data();p=self.fixtures/'bus63.html';p.write_text(p.read_text().replace('★：土曜のみ運行','★：学校休業日は運休'))
  s=self.go();self.assertTrue(s['alerts'])
  for k in ['sansai_gondo_bus','gondo_sansai_bus']:self.assertEqual(before['routes'][k]['times'],self.data()['routes'][k]['times']);self.assertEqual(self.data()['routes'][k]['status'],'review_required')
 def test_future_revision_preserved(self):
  before=self.data()
  for n in (63,64):
   p=self.fixtures/f'bus{n}.html';p.write_text(p.read_text().replace('2026年3月30日','2027年3月30日'))
  self.assertTrue(self.go()['alerts']);self.assertEqual(before['routes']['sansai_gondo_bus']['times'],self.data()['routes']['sansai_gondo_bus']['times'])
 def test_pdf_bytes_change_preserves_times_and_verified_date(self):
  before=self.data();p=self.fixtures/'shinano.pdf';p.write_bytes(p.read_bytes()+b'\nchanged')
  self.assertTrue(self.go()['alerts']);r=self.data()['routes']['sansai_nagano'];self.assertEqual(r['times'],before['routes']['sansai_nagano']['times']);self.assertEqual(r['status'],'review_required');self.assertEqual(r['lastVerified'],before['routes']['sansai_nagano']['lastVerified'])
 def test_missing_source(self):
  before=self.data();(self.fixtures/'bus64.html').unlink();self.assertTrue(self.go()['alerts']);self.assertEqual(before['routes']['gondo_sansai_bus']['times'],self.data()['routes']['gondo_sansai_bus']['times'])
 def test_new_pdf_link_detected(self):
  p=self.fixtures/'shinano.html';p.write_text(p.read_text().replace('20260314_time_table.pdf','20270314_time_table.pdf'));s=self.go();self.assertIn('shinano_page',s['changedSources']);self.assertEqual(self.data()['routes']['sansai_nagano']['status'],'review_required')
 def test_locally_tampered_rail_is_not_verified(self):
  d=self.data();d['routes']['asahi_gondo']['times'][0][0]='05:35';(self.root/'data.json').write_text(json.dumps(d));self.assertTrue(self.go()['alerts']);self.assertEqual(self.data()['routes']['asahi_gondo']['status'],'review_required')
 def test_invalid_time_and_duplicate_rejected(self):
  for times in [[['09:99','10:00','all']],[['10:00','09:00','all']],[['09:00','10:00','all']]*2]:
   with self.assertRaises(ValueError):validate_route({'times':times})
 def test_holiday_truncation_rejected(self):
  with self.assertRaises(ValueError):holiday_candidate(b'date,name\n',{},'2026-11-16')
 def test_bus_parser_full_count(self):
  a=bus((self.fixtures/'bus63.html').read_bytes(),63);b=bus((self.fixtures/'bus64.html').read_bytes(),64);self.assertEqual(sum(len(t) for p in (a,b) for t in p['routes'].values()),33)
 def test_every_registered_rail_pair_has_official_column_evidence(self):
  pairs=json.loads((ROOT/'evidence/rail-pairs.json').read_text())
  for k,ts in pairs.items():
   for t in self.data()['routes'][k]['times']:self.assertIn(t[:2],ts,(k,t))
 def test_original_audit_covers_168_and_counts_discrepancies(self):
  a=json.loads((ROOT/'evidence/verification-168.json').read_text())
  self.assertEqual(len(a),168);self.assertEqual(sum(not x['timeMatch'] for x in a),7);self.assertEqual(sum(not x['dayMatch'] for x in a),5)
 def test_repeated_failure_never_accepts_changed_hash(self):
  p=self.fixtures/'nagaden.pdf';p.write_bytes(p.read_bytes()+b'changed');before=(self.root/'source-state.json').read_text();self.go();self.go();after=json.loads((self.root/'source-state.json').read_text());self.assertEqual(json.loads(before)['nagaden_pdf']['sha256'],after['nagaden_pdf']['sha256'])
if __name__=='__main__':unittest.main()
