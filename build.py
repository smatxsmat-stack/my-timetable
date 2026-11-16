#!/usr/bin/env python3
import json,hashlib,shutil,html
from pathlib import Path
ROOT=Path(__file__).resolve().parent
DIST=ROOT/'dist'
def build():
 DIST.mkdir(exist_ok=True)
 package={k:json.loads((ROOT/f).read_text()) for k,f in [('data','data.json'),('holidays','holidays.json'),('status','monitor-status.json')]}
 content=json.dumps(package,ensure_ascii=False,separators=(',',':'))
 (DIST/'bundle.json').write_text(content)
 (DIST/'bundle.js').write_text('const BUILTIN='+content.replace('<','\\u003c')+';')
 for f in ['index.html','style.css','core.js','app.js','manifest.webmanifest']:
  shutil.copyfile(ROOT/f,DIST/f)
 shutil.copytree(ROOT/'icons',DIST/'icons',dirs_exist_ok=True)
 audit=json.loads((ROOT/'evidence/verification-168.json').read_text())
 rows=''.join('<tr><td>'+html.escape(x['route'])+'</td><td>'+html.escape(', '.join(x['original']))+'</td><td>'+html.escape(', '.join(x['verified']))+'</td><td>'+html.escape(' / '.join(x['notes']) or '一致')+'</td></tr>' for x in audit)
 (DIST/'verification.html').write_text('<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="style.css"><title>168件の照合結果</title><main class="wrap"><a href="./">← 時刻表へ</a><h1>既存168件の照合結果</h1><p>2026-11-16に公式資料で照合。発時刻7件、曜日5件の不一致を修正（重複2件）。長野電鉄上りのB特急4件に種別表示を補完。元データをソースZIP内に保存しています。</p><p>運転日注記を目視照合。鉄道の平日限定便は12月30日〜1月3日も運休。元の holiday（旧版では土日祝扱い）は weekend に明確化しました。網羅性の検証ではありません。</p><div style="overflow:auto"><table style="font-size:12px;border-collapse:collapse" border="1" cellpadding="8"><tr><th>方向</th><th>旧登録</th><th>照合後</th><th>結果</th></tr>'+rows+'</table></div></main></html>')
 assets=['./','./index.html','./style.css','./core.js','./app.js','./bundle.js','./bundle.json','./manifest.webmanifest','./icons/icon-192.png','./icons/icon-512.png','./verification.html']
 digest=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(DIST.rglob('*')) if p.is_file() and p.name!='sw.js')).hexdigest()[:16]
 sw='''const CACHE='mytt-__VERSION__';const ASSETS=__ASSETS__;
self.addEventListener('install',e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS)).then(()=>self.skipWaiting())));
self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('mytt-')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',e=>{const u=new URL(e.request.url);if(e.request.method!=='GET'||u.origin!==self.location.origin)return;
if(u.pathname.endsWith('/bundle.json')){e.respondWith(fetch(e.request).then(async r=>{if(!r.ok)throw Error('HTTP');const clone=r.clone();const v=await clone.json();if(v.data?.schemaVersion!==3||!v.holidays?.days||!v.status)throw Error('schema');const c=await caches.open(CACHE);await c.put(e.request,r.clone());return r}).catch(async()=>{const r=await caches.match(e.request);if(!r)return Response.error();const h=new Headers(r.headers);h.set('X-Timetable-Offline','1');return new Response(await r.arrayBuffer(),{status:r.status,headers:h})}));return;}
e.respondWith(caches.match(e.request).then(r=>r||fetch(e.request)));});
'''.replace('__VERSION__',digest).replace('__ASSETS__',json.dumps(assets))
 (DIST/'sw.js').write_text(sw)
 print('Built',len(assets),'offline assets; version',digest)
if __name__=='__main__':build()
