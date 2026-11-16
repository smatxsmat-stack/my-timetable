"""Strict official HTML adapter. Any unsupported structure/annotation fails closed."""
import re, hashlib, html, json
from html.parser import HTMLParser
SOURCES={
 'shinano_page':'https://www.shinanorailway.co.jp/rail-info/time-table/',
 'shinano_pdf':'https://www.shinanorailway.co.jp/rail-info/time-table/docs/20260314_time_table.pdf',
 'nagaden_page':'https://www.nagaden-net.co.jp/info/timetable/',
 'nagaden_pdf':'https://www.nagaden-net.co.jp/hubfs/ikoku20210313-01-1.pdf?hsLang=ja',
 'bus63':'https://www.nagadenbus.co.jp/local/diagram/diagram_p.php?route=NGN02',
 'bus64':'https://www.nagadenbus.co.jp/local/diagram/diagram_p.php?route=NGN04',
 'holidays':'https://www8.cao.go.jp/chosei/shukujitsu/syukujitsu.csv'}
def sha(b):return hashlib.sha256(b).hexdigest()
def clean(s):return re.sub(r'\s+','',html.unescape(re.sub('<[^>]+>','',s)))
def bus(raw,line):
 s=raw.decode('utf-8');parts=re.split(r'<h2[^>]*>',s)[1:]
 if len(parts)!=4:raise ValueError('Expected four direction/day tables')
 trips={'sansai_gondo_bus':[],'gondo_sansai_bus':[]}; dates=set();shapes=[]
 for part in parts:
  heading=clean(part.split('</h2>')[0]);table=re.search(r'<table\b.*?</table>',part,re.S)
  if not table:raise ValueError('Missing table')
  table=table.group(); rev=re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日改正',part)
  if not rev:raise ValueError('Missing revision')
  dates.add('%04d-%02d-%02d'%tuple(map(int,rev.groups())))
  day='weekday' if '[平日]' in heading else 'weekend' if '[土曜日・休日]' in heading else None
  if not day:raise ValueError('Unknown service day')
  rows=[]
  for row in re.findall(r'<tr\b.*?</tr>',table,re.S):
   cells=re.findall(r'<t[hd]\b[^>]*>(.*?)</t[hd]>',row,re.S)
   rows.append([clean(c) for c in cells])
  stops={r[0]:r[2:] for r in rows if len(r)>2 and r[1] in ('発','着') and r[0]}
  if any(k not in stops for k in ['権堂','三才駅','三才駅(県道)']):raise ValueError('Missing stops')
  n=len(stops['権堂'])
  if not n or any(len(v)!=n for v in stops.values()):raise ValueError('Unequal column lengths')
  star=[False]*n
  for r in rows:
   if r[0]=='':
    if len(r[1:])==n:
     for i,v in enumerate(r[1:]):
      if v not in ('','★'):raise ValueError('Unknown annotation')
      star[i]=v=='★'
  if any(star) and '★：土曜のみ運行' not in clean(part):raise ValueError('Unknown star definition')
  inbound='長野駅' in heading
  key='sansai_gondo_bus' if inbound else 'gondo_sansai_bus'
  def tm(v):
   if v in ('↓↓','↑↑','…','・・・',''):return None
   if not re.fullmatch(r'\d{1,2}:\d{2}',v):raise ValueError('Unknown time cell '+v)
   h,m=map(int,v.split(':'))
   if not 0<=h<24 or not 0<=m<60:raise ValueError('Invalid time')
   return f'{h:02}:{m:02}'
  for i in range(n):
   g=tm(stops['権堂'][i])
   for stop in ['三才駅(県道)','三才駅']:
    a=tm(stops[stop][i])
    if not a or not g:continue
    dep,arr=(a,g) if inbound else (g,a)
    if arr<=dep:raise ValueError('Arrival precedes departure')
    trips[key].append([dep,arr,'saturday' if star[i] else day,str(line),'三才駅前' if stop=='三才駅' else stop])
  # Exact non-time content includes stop order, notes, column count, headings.
  region=part.split('</section>')[0]
  shape=clean(region)
  shape=re.sub(r'\d{4}年\d{1,2}月\d{1,2}日改正','REVISION',shape)
  shape=re.sub(r'\d{1,2}:\d{2}','TIME',shape)
  shapes.append(shape)
 if len(dates)!=1:raise ValueError('Mixed revisions')
 return {'routes':trips,'validFrom':dates.pop(),'shape':sha(json.dumps(shapes,ensure_ascii=False).encode())}
