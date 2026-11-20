(function(root){
'use strict';
const DAYS=['all','weekday','saturday','holiday','weekend'];
function minutes(t){return Number(t.slice(0,2))*60+Number(t.slice(3));}
function validTime(t){return /^(?:[01]\d|2[0-3]):[0-5]\d$/.test(t);}
function japanNow(now=new Date()){const p=Object.fromEntries(new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(now).map(x=>[x.type,x.value]));return {date:`${p.year}-${p.month}-${p.day}`,time:`${p.hour}:${p.minute}`};}
function dayKind(date,calendar){if(!/^\d{4}-\d{2}-\d{2}$/.test(date)||date<calendar.validFrom||date>calendar.validThrough)return 'unknown';if(calendar.days[date])return 'holiday';const d=new Date(date+'T12:00:00+09:00').getUTCDay();return d===0?'holiday':d===6?'saturday':'weekday';}
function routeDay(route,date,kind){const md=date.slice(5);if(route.busSpecialCalendar){if(md==='01-01')return 'closed';if(md>='12-29'||md<='01-03'||(md>='08-13'&&md<='08-16'))return kind==='saturday'?'saturday':kind==='unknown'?'unknown':'holiday';}return kind;}
function operates(trip,route,date,kind){const d=routeDay(route,date,kind);if(['unknown','closed'].includes(d))return false;if(trip[2]==='weekday'&&(route.weekdayExcludedMonthDays||[]).includes(date.slice(5)))return false;return trip[2]==='all'||trip[2]===d||(trip[2]==='weekend'&&['holiday','saturday'].includes(d));}
function tripOrigin(key,r,t){if(r.type!=='bus')return r.from;if(key==='sansai_gondo_bus')return t[4]||'三才駅付近';return '権堂バス停';}
function trips(db,{origin='all',direction='all',date,time,kind,extras={}}){let list=[];for(const [key,r]of Object.entries(db.routes)){if(direction==='go'&&!['sansai_nagano','asahi_gondo','sansai_gondo_bus'].includes(key))continue;if(direction==='back'&&!['nagano_sansai','gondo_asahi','gondo_sansai_bus'].includes(key))continue;for(const [i,t]of [...r.times,...(extras[key]||[])].entries()){const from=tripOrigin(key,r,t);if(origin!=='all'&&origin!==from)continue;if(operates(t,r,date,kind)&&minutes(t[0])>=minutes(time))list.push({key,route:r,trip:t,from,custom:i>=r.times.length});}}return list.sort((a,b)=>minutes(a.trip[0])-minutes(b.trip[0])||a.key.localeCompare(b.key));}
function parseExtras(s){return s.split(/\r?\n/).filter(x=>x.trim()).map(line=>{const t=line.split(',').map(x=>x.trim());if(t.length<2||t.length>5||!t.slice(0,2).every(validTime)||minutes(t[1])<=minutes(t[0]))throw Error('発着時刻を HH:MM で入力し、到着を出発より後にしてください。');t[2]=t[2]||'all';if(!DAYS.includes(t[2]))throw Error('曜日は all / weekday / saturday / holiday / weekend です。');return t;});}
function validData(d){return d?.schemaVersion===3&&d.routes&&Object.keys(d.routes).length===6&&Object.values(d.routes).every(r=>Array.isArray(r.times)&&r.times.length>0&&r.times.every(t=>Array.isArray(t)&&t.slice(0,2).every(validTime)&&DAYS.includes(t[2])));}
// Fare records are independent of the preserved timetable rows.
function fareFor(fares,key,t,date,custom=false){
 const id=key.endsWith('_bus')?'bus'+t[3]:['sansai_nagano','nagano_sansai'].includes(key)?'shinano':'nagaden';
 const f=fares?.groups?.[id];
 if(custom||!f||f.status!=='verified'||date<f.validFrom)return '大人運賃：未確認';
 if(key.endsWith('_bus')&&t[4]!=='三才駅前')return '大人運賃：未確認（県道停留所）';
 if(!Number.isInteger(f.cash)||f.cash<=0)return '大人運賃：未確認';
 if(id==='shinano')return `大人 きっぷ ${f.cash}円 / IC ${Number.isInteger(f.ic)?f.ic+'円':'未確認'}`;
 if(id==='nagaden'){
  if(t[3]&&t[3]!=='B特急')return '大人運賃：未確認（種別要確認）';
  if(t[3]==='B特急')return Number.isInteger(f.express)?`大人 ${f.cash+f.express}円（普通${f.cash}円＋特急${f.express}円）`:'大人 特急料金：未確認';
  return `大人 普通 ${f.cash}円（IC直接乗車不可）`;
 }
 return `大人 現金 ${f.cash}円 / IC 未確認`;
}
// Always use today's actual JST calendar, independent of the search controls.
// Custom/temporary departures and the next day's service are deliberately excluded.
function lastServices(db,calendar,approved,now=japanNow()){
 const kind=dayKind(now.date,calendar),out=[];
 for(const [key,r]of Object.entries(db.routes)){
  const isBus=r.type==='bus',proof=approved?.rail?.[key];
  const source=isBus?r.times:(proof?.times||[]);
  const groups=isBus?[...new Map(r.times.map(t=>[`${t[3]}|${t[4]}`,[t[3],t[4]]])).values()]:[['','']];
  for(const [line,stop]of groups){
   const from=isBus?(key==='sansai_gondo_bus'?stop:'権堂バス停'):r.from;
   const to=isBus?(key==='sansai_gondo_bus'?'権堂バス停':stop):r.to;
   const entry={key,label:isBus?`長電バス ${line}系統`:r.label,from,to,time:null,state:'unknown'};
   const verified=r.status==='verified'&&now.date>=r.validFrom&&(isBus||(proof?.verified===true&&now.date>=proof.validFrom));
   if(verified&&kind!=='unknown'){
    const eligible=source.filter(t=>(!isBus||(t[3]===line&&t[4]===stop))&&operates(t,r,now.date,kind));
    const last=eligible.sort((a,b)=>minutes(b[0])-minutes(a[0]))[0];
    if(!last)entry.state='no_service';
    else{entry.time=last[0];entry.state=minutes(now.time)>minutes(last[0])?'ended':minutes(now.time)===minutes(last[0])?'departing':'upcoming';}
   }
   out.push(entry);
  }
 }
 return out;
}
const api={fareFor,lastServices,minutes,validTime,japanNow,dayKind,routeDay,operates,trips,parseExtras,validData};if(typeof module!=='undefined')module.exports=api;else root.Timetable=api;
})(typeof window==='undefined'?globalThis:window);
