#!/usr/bin/env python3
"""Fetch, compare, validate, then atomically promote only supported official data.
Never use a language model or guessed times. Unknown PDF revisions require review.
"""
import argparse,copy,csv,datetime,difflib,json,re,sys,urllib.request,os
from pathlib import Path
from zoneinfo import ZoneInfo
from sources import SOURCES,sha,bus
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text())
def write(p,v):
 p.parent.mkdir(parents=True,exist_ok=True);q=p.with_suffix(p.suffix+'.tmp');q.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');q.replace(p)
def fetch(url):
 req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; PersonalTimetable/1.0)'})
 with urllib.request.urlopen(req,timeout=35) as r:
  if urlparse(r.geturl()).scheme!='https':raise ValueError('Non-HTTPS redirect')
  b=r.read(10_000_001)
 if not 500<len(b)<=10_000_000:raise ValueError('Unexpected response size')
 if '.pdf' in url and not b.startswith(b'%PDF-'):raise ValueError('Not PDF')
 return b
# urlparse is from urllib.parse, not urllib.request on every Python.
from urllib.parse import urlparse,urljoin

def validate_route(r):
 ts=r['times']
 if not isinstance(ts,list) or not 1<=len(ts)<=300:raise ValueError('Invalid trip count')
 seen=set()
 for t in ts:
  if not 3<=len(t)<=5 or any(not isinstance(x,str) for x in t):raise ValueError('Invalid trip fields')
  for v in t[:2]:
   if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',v):raise ValueError('Invalid time')
  if t[0]>=t[1]:raise ValueError('Invalid arrival')
  if t[2] not in ('all','weekday','saturday','holiday','weekend'):raise ValueError('Unknown calendar')
  if tuple(t) in seen:raise ValueError('Duplicate trip')
  seen.add(tuple(t))

def holiday_candidate(b,previous,today):
 rows=list(csv.reader(b.decode('cp932').splitlines()))
 if len(rows)<100:raise ValueError('Holiday CSV too short')
 days={}
 for row in rows[1:]:
  if len(row)!=2:raise ValueError('Holiday CSV columns')
  day=datetime.datetime.strptime(row[0],'%Y/%m/%d').date().isoformat()
  if day in days:raise ValueError('Duplicate holiday')
  days[day]=row[1]
 for y in {s[:4] for s in days}:
  if not (16 if int(y)>=2020 else 8)<=sum(k.startswith(y) for k in days)<=25:raise ValueError('Holiday year incomplete')
 end=max(days)[:4]+'-12-31'
 if end<previous['validThrough']:raise ValueError('Holiday coverage shrunk')
 if any(k not in days or days[k]!=v for k,v in previous['days'].items() if k<today):raise ValueError('Historical holidays changed')
 return dict(previous,days=days,validThrough=end,checkedAt=today)

def run(root=ROOT,fixture=None,today=None):
 today=today or datetime.datetime.now(ZoneInfo('Asia/Tokyo')).date().isoformat()
 data=read(root/'data.json');base=read(root/'source-state.json');state=copy.deepcopy(base);nextdata=copy.deepcopy(data)
 alerts=[];changes=[];raw={};errors={};observed={};report=root/'reports';report.mkdir(exist_ok=True)
 for k,u in SOURCES.items():
  try:
   if fixture:
    name=k.replace('_page','.html').replace('_pdf','.pdf') if k.startswith(('shinano','nagaden')) else k+('.csv' if k=='holidays' else '.html')
    b=(fixture/name).read_bytes()
   else:b=fetch(u)
   raw[k]=b;observed[k]={'sha256':sha(b),'url':u,'checkedAt':today}
   if k.endswith('_pdf') and not b.startswith(b'%PDF-'):raise ValueError('Invalid PDF')
   if sha(b)!=base[k]['sha256']:
    changes.append(k)
    if k.endswith('_pdf'):
     try:
      from pdf_compare import compare
      compare((root/'evidence'/(k.replace('_pdf','.pdf'))).read_bytes(),b,report/(k+'-comparison.diff'))
     except Exception as e:(report/(k+'-comparison-error.txt')).write_text('PDF比較不能。自動更新禁止: '+str(e))
    (report/(k+('.pdf' if k.endswith('_pdf') else '.txt'))).write_bytes(b)
    oldfile=root/'evidence'/(k.replace('_page','.html').replace('_pdf','.pdf') if k.startswith(('shinano','nagaden')) else k+('.csv' if k=='holidays' else '.html'))
    if not k.endswith('_pdf') and oldfile.exists():
     diff=''.join(difflib.unified_diff(oldfile.read_bytes().decode('utf-8','replace').splitlines(True),b.decode('utf-8','replace').splitlines(True),fromfile='accepted',tofile='official-candidate'))
     (report/(k+'.diff')).write_text(diff)
  except Exception as e:errors[k]=str(e);alerts.append({'source':k,'reason':'取得・形式確認失敗: '+str(e)})
 # PDF URLs in index pages must also be monitored, including renamed documents.
 for provider in ('shinano','nagaden'):
  ids=[provider+'_page',provider+'_pdf'];routes=[k for k,r in data['routes'].items() if r['sourceIds']==ids]
  if any(k in errors or k in changes for k in ids):
   for k in routes:nextdata['routes'][k]['status']='review_required'
   alerts.append({'source':provider,'reason':'公式PDFまたは案内ページの変更・取得失敗。既存時刻を維持し、手動で全列と注記を再検証してください。'})
   if provider+'_page' in raw:
    page=raw[provider+'_page'].decode('utf-8','replace')
    links=[urljoin(SOURCES[provider+'_page'],htmlurl.replace('&amp;','&')) for htmlurl in re.findall(r'href=[\"\']([^\"\']+\.pdf[^\"\']*)',page,re.I)]
    links=[u for u in links if urlparse(u).hostname==urlparse(SOURCES[provider+'_page']).hostname and ('time_table' in u if provider=='shinano' else ('ikoku' in u or 'jikoku' in u))]
    write(report/(provider+'-pdf-links.json'),links)
    if not fixture:
     for j,u in enumerate(links[:4]):
      try:
       candidate=fetch(u);(report/f'{provider}-candidate-{j}.pdf').write_bytes(candidate)
       from pdf_compare import compare
       compare((root/'evidence'/f'{provider}.pdf').read_bytes(),candidate,report/f'{provider}-candidate-{j}.diff')
      except Exception as e:alerts.append({'source':provider,'reason':'新PDF取得失敗: '+str(e)})
  else:
   approved=read(root/'evidence/approved-rail.json')
   for k in routes:
    # A checksum of the source does not validate locally edited travel times.
    if data['routes'][k]['times']!=approved[k]['times']:
     nextdata['routes'][k]['status']='review_required';alerts.append({'source':k,'reason':'データが検証済みスナップショットと不一致'})
    else:nextdata['routes'][k].update(status='verified',lastVerified=today)
   for k in ids:state[k]['lastChecked']=today
 try:
  if any(k not in raw or k in errors for k in ('bus63','bus64')):raise ValueError('両系統の取得が必要です')
  parsed=[bus(raw['bus'+str(n)],n) for n in (63,64)]
  for n,p in zip((63,64),parsed):
   if p['shape']!=base['bus'+str(n)]['shape']:raise ValueError('表構造・注記・停留所・便数が変更されています')
  if len({p['validFrom'] for p in parsed})!=1:raise ValueError('系統間の改正日が一致しません')
  revision=parsed[0]['validFrom']
  if revision>today:raise ValueError('将来の改正日です。施行日までは現行データを維持します')
  for k in ('sansai_gondo_bus','gondo_sansai_bus'):
   r=copy.deepcopy(data['routes'][k]);r['times']=sum([p['routes'][k] for p in parsed],[])
   validate_route(r)
   if sorted(r['times'])==sorted(data['routes'][k]['times']):r['times']=data['routes'][k]['times']
   if revision<r['validFrom']:raise ValueError('改正日が過去に戻っています')
   r.update(status='verified',lastVerified=today,validFrom=revision)
   nextdata['routes'][k]=r
  for k in ('bus63','bus64'):
   state[k].update(sha256=sha(raw[k]),lastChecked=today)
 except Exception as e:
  alerts.append({'source':'bus','reason':str(e)})
  for k in ('sansai_gondo_bus','gondo_sansai_bus'):
   nextdata['routes'][k]=copy.deepcopy(data['routes'][k]);nextdata['routes'][k]['status']='review_required'
 cal=read(root/'holidays.json')
 try:
  if 'holidays' in errors:raise ValueError(errors['holidays'])
  cal=holiday_candidate(raw['holidays'],cal,today);state['holidays'].update(sha256=sha(raw['holidays']),lastChecked=today)
 except Exception as e:alerts.append({'source':'holidays','reason':str(e)})
 diff=[]
 for k,r in nextdata['routes'].items():
  validate_route(r)
  before=data['routes'][k]['times'];after=r['times']
  if before!=after:diff.append({'route':k,'old':before,'new':after,'removed':[x for x in before if x not in after],'added':[x for x in after if x not in before]})
 if diff:nextdata['updated']=today
 faredata=None
 if (root/'fares.json').exists():
  from fare_monitor import check
  farefetch=fetch
  if fixture:
   fareurls={s['url']:s['file'] for s in read(root/'fares.json')['sources'].values()}
   farefetch=lambda url:(fixture/'fares'/fareurls[url]).read_bytes()
  faredata,fa,fc,fo=check(root,farefetch,today)
  alerts.extend(fa);changes.extend(fc);observed.update(fo)
 status={'checkedAt':today,'alerts':alerts,'changedSources':changes,'updatedRoutes':[x['route'] for x in diff],'message':'公式資料を取得・確認しました。'+('GitHub Actionsで実行。' if os.environ.get('GITHUB_ACTIONS')=='true' else '定期監視はGitHubでの設定が必要です。')}
 # All validation finishes before publishing any file. CI deploys these in one commit.
 write(report/'comparison.json',{'date':today,'sourceChanges':changes,'timeDiff':diff,'alerts':alerts,'observed':observed})
 if faredata is not None:write(root/'fares.json',faredata)
 write(root/'data.json',nextdata);write(root/'source-state.json',state);write(root/'holidays.json',cal);write(root/'monitor-status.json',status)
 for k,v in state.items():
  if k in raw and v['sha256']==sha(raw[k]):
   name=k.replace('_page','.html').replace('_pdf','.pdf') if k.startswith(('shinano','nagaden')) else k+('.csv' if k=='holidays' else '.html')
   (root/'evidence'/name).write_bytes(raw[k])
 print(json.dumps(status,ensure_ascii=False));return status
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--fixtures',type=Path);parser.add_argument('--date');a=parser.parse_args()
 run(fixture=a.fixtures,today=a.date)
