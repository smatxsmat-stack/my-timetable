'use strict';
const T=Timetable,$=id=>document.getElementById(id),esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let db=BUILTIN.data,calendar=BUILTIN.holidays,status=BUILTIN.status,fares=BUILTIN.fares,lastProof=BUILTIN.lastServices,live=true,direction='all',origin='all',cachedData=false;
function get(k){try{return localStorage.getItem(k)}catch{return null}}function put(k,v){localStorage.setItem(k,v)}
origin=get('mytt-origin')||'all';
const origins=[['all','すべて','電車・バス'],['三才駅','三才駅','北しなの線'],['長野駅','長野駅','北しなの線'],['朝陽駅','朝陽駅','長野電鉄'],['権堂駅','権堂駅','長野電鉄'],['三才駅(県道)','三才駅(県道)','長電バス'],['三才駅前','三才駅前','長電バス'],['権堂バス停','権堂バス停','長電バス']];
if(!origins.some(x=>x[0]===origin))origin='all';
function extras(k){try{const current=get('mytt-v3-'+k);let a=JSON.parse(current||get('mytt-v2-'+k)||'[]');if(!Array.isArray(a))return [];if(!current)a=a.map(t=>t.map((v,i)=>i===2&&v==='holiday'?'weekend':v));return T.parseExtras(a.map(t=>t.join(',')).join('\n'))}catch{return []}}
function updateNow(){const n=T.japanNow();$('date').value=n.date;$('time').value=n.time;}
function render(){
 const n=T.japanNow();$('liveClock').textContent=`${n.date.replaceAll('-',' / ')}　${n.time}　JST${live?' · 現在時刻に追従中':' · 指定時刻で検索中'}`;
 const date=$('date').value,time=$('time').value,override=$('day').value;const kind=override==='auto'?T.dayKind(date,calendar):override;
 const names={weekday:'平日',saturday:'土曜',holiday:'日曜・祝日',unknown:'祝日データの範囲外'};
 $('dayLabel').textContent=(calendar.days[date]||names[kind])+(override!=='auto'?'・手動指定':'');
 $('origins').innerHTML=origins.map(([id,label,sub])=>`<button data-origin="${esc(id)}" aria-pressed="${origin===id}">${esc(label)}<small>${esc(sub)}</small></button>`).join('');
 document.querySelectorAll('[data-direction]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.direction===direction));
 const extra=Object.fromEntries(Object.keys(db.routes).map(k=>[k,extras(k)]));
 const rows=T.trips(db,{date,time,kind,origin,direction,extras:extra});
 $('count').textContent=`${time}以降 · ${rows.length}件`;
 $('tripList').innerHTML=rows.length?rows.map(({key,route:r,trip:t,from,custom})=>{const delta=T.minutes(t[0])-T.minutes(time);const dest=key==='gondo_sansai_bus'?t[4]:r.to;const unverified=r.status!=='verified'||date<r.validFrom;return `<article class="trip"><div><div class="depart">${esc(t[0])}</div><div class="arrive">${esc(t[1])} 着</div></div><div><div class="routeName">${esc(r.label)}</div><div class="destination">${esc(from)} → ${esc(dest)}</div>${t[3]?`<span class="badge">${esc(t[3])}${r.type==='bus'?'系統':'・特急券必要'}</span>`:''}${custom?'<span class="badge warn">端末追加・未検証</span>':unverified?'<span class="badge warn">再検証が必要・旧登録時刻</span>':''}<div class="fare">${esc(T.fareFor(fares,key,t,date,custom))}</div><div class="detail">${t[2]==='weekday'?'平日限定 · 年末年始除く':t[2]==='saturday'?'土曜のみ':t[2]==='weekend'?'土日祝':''}</div></div><div class="countdown">${live?'あと':'指定時刻から'}<strong>${delta}</strong>分</div></article>`}).join(''):`<div class="empty">${kind==='unknown'?'祝日データの範囲外です。<br>公式を確認して運行日を手動指定してください。':'この条件で表示できる登録便はありません。<br>日付・出発地を変えるか、公式時刻表をご確認ください。'}</div>`;
 const finals=T.lastServices(db,calendar,lastProof,n);
 $('lastDate').textContent=`${n.date} · ${names[T.dayKind(n.date,calendar)]} · 日本時間`;
 $('lastList').innerHTML=finals.map(x=>`<div class="lastRow"><div><strong>${esc(x.label)}</strong><div>${esc(x.from)} → ${esc(x.to)}</div></div><div class="lastTime">${x.time?`<strong>${esc(x.time)}</strong><br>`:''}${x.state==='ended'?'本日の運行終了':x.state==='no_service'?'本日は運行なし':x.state==='unknown'?'最終便未確認':x.state==='departing'?'発車時刻です':'最終便'}</div></div>`).join('');
 $('fareSources').innerHTML=Object.values(fares?.groups||{}).map(f=>`<section class="source"><h3>${esc(f.label)}</h3><p>${f.status==='verified'?'公式運賃を確認済み':'変更・取得失敗：料金表示を保留'} · 改定 ${esc(f.validFrom)} · 最終照合 ${esc(f.lastVerified)}</p><p>${esc(f.note)}</p>${f.sourceIds.map(id=>`<a href="${esc(fares.sources[id].url)}" target="_blank" rel="noopener">公式資料 ↗</a>`).join(' · ')}</section>`).join('');
 let warnings=[];if(status.alerts?.length)warnings.push('公式資料の変更または取得エラーがあります。時刻は既存データを保持し、未検証の料金・最終便は表示を保留します。検証状況を確認してください。');
 if(date.slice(5)==='01-01')warnings.push('1月1日は長電バス63・64系統が全便運休です。');
 if((date.slice(5)>='12-29'||date.slice(5)<='01-03'||(date.slice(5)>='08-13'&&date.slice(5)<='08-16'))&&date.slice(5)!=='01-01')warnings.push('長電バスは年末年始・お盆の土休日ダイヤです。');
 if(Object.values(db.routes).some(r=>date<r.validFrom))warnings.push('選択日は登録ダイヤの改正日より前です。過去の運行は検証できません。');
 if(override!=='auto')warnings.push('運行日を手動指定しています。日付の実際の曜日と異なる便を表示する場合があります。');
 $('warning').hidden=!warnings.length;$('warning').textContent=warnings.join(' ');
 $('connection').hidden=navigator.onLine&&!cachedData;$('connection').textContent='オフラインです。保存済みの時刻表を表示しています。最新の変更は確認できません。';
 $('sources').innerHTML=Object.entries(db.routes).map(([k,r])=>`<section class="source"><h3>${esc(r.from)} → ${esc(r.to)}</h3><span class="badge ${r.status==='verified'?'':'warn'}">${r.status==='verified'?'登録便を公式照合済み':'検証できない変更あり・既存データを維持'}</span><p>公式改正日 ${esc(r.validFrom)}<br>最終照合日 ${esc(r.lastVerified||'未確認')}</p><p>${esc(r.coverage)} ${esc(r.note)}</p><a href="${esc(r.url)}" target="_blank" rel="noopener">公式時刻表 ↗</a> ${r.url2?` · <a href="${esc(r.url2)}" target="_blank" rel="noopener">64系統 ↗</a>`:''}</section>`).join('');
 $('monitor').textContent=`最終取得確認：${status.checkedAt||'未確認'}。${status.message||''} ${(status.alerts||[]).map(a=>`${a.source}：${a.reason}`).join(' / ')}`;
 $('holidayCoverage').textContent=`${calendar.validThrough}まで収録`;
}
$('origins').addEventListener('click',e=>{const b=e.target.closest('[data-origin]');if(!b)return;origin=b.dataset.origin;direction='all';try{put('mytt-origin',origin)}catch{}render()});
document.querySelectorAll('[data-direction]').forEach(b=>b.addEventListener('click',()=>{direction=b.dataset.direction;origin='all';render()}));
for(const id of ['date','time'])$(id).addEventListener('change',()=>{if(!$(id).value){updateNow()}live=false;render()});
$('day').addEventListener('change',render);$('now').onclick=()=>{live=true;$('day').value='auto';updateNow();render()};
$('extraRoute').innerHTML=Object.entries(db.routes).map(([k,r])=>`<option value="${k}">${esc(r.from)} → ${esc(r.to)}</option>`).join('');
function loadExtra(){$('extraText').value=extras($('extraRoute').value).map(t=>t.join(',')).join('\n')}$('extraRoute').onchange=loadExtra;loadExtra();
$('saveExtra').onclick=()=>{try{const a=T.parseExtras($('extraText').value);put('mytt-v3-'+$('extraRoute').value,JSON.stringify(a));$('saveMessage').textContent='保存しました（端末追加・未検証）。';render()}catch(e){$('saveMessage').textContent=e.message}};
updateNow();render();setInterval(()=>{if(live)updateNow();render()},15000);document.addEventListener('visibilitychange',()=>{if(!document.hidden){if(live)updateNow();render()}});window.addEventListener('online',render);window.addEventListener('offline',render);
let refreshing=false;navigator.serviceWorker?.addEventListener('controllerchange',()=>{if(!refreshing){refreshing=true;location.reload()}});
let installPrompt;window.addEventListener('beforeinstallprompt',e=>{e.preventDefault();installPrompt=e;$('install').hidden=false});$('install').onclick=async()=>{if(installPrompt){await installPrompt.prompt();installPrompt=null;$('install').hidden=true}};
if('serviceWorker'in navigator&&location.protocol!=='file:')navigator.serviceWorker.register('./sw.js').then(()=>navigator.serviceWorker.ready).then(()=>{$('offlineReady').textContent='オフライン表示の準備ができました。'}).catch(()=>{$('offlineReady').textContent='オフライン準備に失敗しました。オンラインで再読み込みしてください。'});
async function refresh(){try{const response=await fetch('./bundle.json',{cache:'no-store'});if(!response.ok)return;cachedData=response.headers.get('X-Timetable-Offline')==='1';const next=await response.json();if(!T.validData(next.data)||!next.holidays?.days||!next.status)return;db=next.data;calendar=next.holidays;status=next.status;fares=next.fares;lastProof=next.lastServices;render()}catch{}}if(location.protocol!=='file:')refresh();
