import unittest,sys,tempfile,shutil,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from fare_monitor import check
class FareTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  shutil.copy(ROOT/'fares.json',self.root);shutil.copytree(ROOT/'evidence/fares',self.root/'evidence/fares')
  self.original=json.loads((self.root/'fares.json').read_text());self.byurl={s['url']:(self.root/'evidence/fares'/s['file']).read_bytes() for s in self.original['sources'].values()}
 def test_unchanged(self):
  data,alerts,changes,_=check(self.root,self.byurl.__getitem__,'2026-11-19');self.assertEqual(alerts,[]);self.assertEqual(changes,[]);self.assertTrue(all(x['status']=='verified' for x in data['groups'].values()))
 def test_changed_fare_preserves_values_and_requires_review(self):
  u=self.original['sources']['bus63.html']['url'];self.byurl[u]=self.byurl[u].replace('650円'.encode(),'999円'.encode())
  for _ in range(2):
   data,a,c,_=check(self.root,self.byurl.__getitem__,'2026-11-19');self.assertTrue(a);self.assertIn('fare:bus63.html',c);self.assertEqual(data['groups']['bus63']['cash'],650);self.assertEqual(data['groups']['bus63']['status'],'review_required');self.assertEqual(data['groups']['bus64']['status'],'verified')
  self.assertEqual(json.loads((self.root/'fares.json').read_text()),self.original)
 def test_fetch_failure_does_not_change_amount(self):
  def fail(url):raise OSError('offline')
  d,a,_,_=check(self.root,fail,'2026-11-19');self.assertTrue(a);self.assertEqual(d['groups']['shinano']['ic'],242);self.assertTrue(all(x['status']=='review_required' for x in d['groups'].values()))
 def test_new_pdf_link_is_detected(self):
  u=self.original['sources']['shinano-index.html']['url'];self.byurl[u]=self.byurl[u].replace(b'.pdf',b'-revised.pdf')
  d,a,c,_=check(self.root,self.byurl.__getitem__,'2026-11-19');self.assertIn('fare:shinano-index.html',c);self.assertEqual(d['groups']['shinano']['status'],'review_required')
 def test_saved_sources_match_verified_fares(self):
  import pdfplumber
  with pdfplumber.open(ROOT/'evidence/fares/shinano.pdf') as p:
   for page,expected in [(5,'850 650 590 430 260 250 240'),(6,'847 649 583 429 251 242 231')]:self.assertIn(expected,p.pages[page].extract_text())
  with pdfplumber.open(ROOT/'evidence/fares/nagaden.pdf') as p:self.assertIn('朝陽 5.2 300',p.pages[0].extract_text())

 def test_locally_modified_amount_is_not_verified(self):
  p=self.root/'fares.json';d=json.loads(p.read_text());d['groups']['shinano']['cash']=1;p.write_text(json.dumps(d))
  data,alerts,_,_=check(self.root,self.byurl.__getitem__,'2026-11-19');self.assertTrue(alerts);self.assertEqual(data['groups']['shinano']['status'],'review_required')
 def test_combined_monitor_keeps_168_times_when_fares_fail(self):
  from check_updates import run
  import contextlib,io
  shutil.copytree(ROOT/'tests/fixtures',self.root,dirs_exist_ok=True)
  before=json.loads((self.root/'data.json').read_text())
  fixture=self.root/'evidence'
  (fixture/'fares/bus63.html').write_bytes(b'not a fare page')
  with contextlib.redirect_stdout(io.StringIO()):status=run(self.root,fixture,'2026-11-16')
  after=json.loads((self.root/'data.json').read_text());self.assertEqual([r['times'] for r in before['routes'].values()],[r['times'] for r in after['routes'].values()]);self.assertTrue(any(a['source']=='fare:bus63.html' for a in status['alerts']))
  self.assertEqual(json.loads((self.root/'fares.json').read_text())['groups']['bus63']['cash'],650)
