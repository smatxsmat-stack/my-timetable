"""Conservative fare monitoring: new amounts are never promoted without review."""
import copy,difflib,hashlib,json,re

def canonical(raw,filename):
 if filename.endswith('.pdf'):
  if not raw.startswith(b'%PDF-'):raise ValueError('Invalid PDF')
  return raw
 text=raw.decode('utf-8')
 if '<html' not in text.lower():raise ValueError('Invalid HTML')
 text=re.sub(r'<(script|style)\b[^>]*>.*?</\1>','',text,flags=re.S|re.I)
 text=re.sub(r'<!--.*?-->','',text,flags=re.S)
 # Preserve links, tables, notes and dates; ignore layout whitespace only.
 return re.sub(r'\s+',' ',text).encode()

def check(root,fetch,today):
 old=json.loads((root/'fares.json').read_text());next=copy.deepcopy(old)
 alerts=[];changed=[];observed={};bad=set();report=root/'reports';report.mkdir(exist_ok=True)
 for key,source in old['sources'].items():
  try:
   raw=fetch(source['url']);candidate=canonical(raw,source['file'])
   baseline=(root/'evidence/fares'/source['file']).read_bytes()
   expected=canonical(baseline,source['file'])
   if hashlib.sha256(expected).hexdigest()!=source['sha256']:raise ValueError('検証済み資料のハッシュ不一致')
   observed['fare:'+key]={'sha256':hashlib.sha256(candidate).hexdigest(),'url':source['url'],'checkedAt':today}
   if candidate!=expected:
    bad.add(key);changed.append('fare:'+key)
    (report/('fare-'+source['file'])).write_bytes(raw)
    if key.endswith('.pdf'):
     from pdf_compare import compare
     compare(baseline,raw,report/('fare-'+key+'.diff'))
    else:(report/('fare-'+key+'.diff')).write_text(''.join(difflib.unified_diff(baseline.decode().splitlines(True),raw.decode().splitlines(True),fromfile='accepted',tofile='candidate')))
    alerts.append({'source':'fare:'+key,'reason':'公式運賃資料に変更。旧データを保持し、料金の表示を保留。手動照合が必要です。'})
  except Exception as e:
   bad.add(key);alerts.append({'source':'fare:'+key,'reason':'運賃の取得・比較失敗。旧データを保持し料金表示を保留: '+str(e)})
 approved=json.loads((root/'evidence/fares/approved.json').read_text())
 for key,group in next['groups'].items():
  if {k:v for k,v in group.items() if k not in ('status','lastVerified')}!=approved.get(key):
   group['status']='review_required';alerts.append({'source':'fare:'+key,'reason':'料金データが照合済み記録と不一致。表示を保留します。'});continue
  if bad.intersection(group['sourceIds']):group['status']='review_required'
  else:group.update(status='verified',lastVerified=today)
 return next,alerts,changed,observed
