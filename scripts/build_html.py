# -*- coding: utf-8 -*-
"""读取 travel-data.json → 生成移动端单页 index.html（数据内嵌，同源）。

用法：
  python build_html.py <travel-data.json> [out.html]

城市节点 / 视图胶囊从 JSON 的 days[].mapPoints 推导，不写死某条线路。
腾讯地图 JSAPI Key 运行时从 ~/.tencentmap/tempkey.json 读取，包内不携带 Key。
"""
import json, os, sys, hashlib, re
from html import escape
from urllib.parse import quote
from check_deps import load_tmap_key


def script_json(value):
    """JSON 字符串也会被 HTML 的 </script> 截断，必须在嵌入前转义。"""
    return (json.dumps(value, ensure_ascii=False, separators=(',', ':'))
            .replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e')
            .replace('\u2028', '\\u2028').replace('\u2029', '\\u2029'))

SRC = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.getcwd(), 'travel-data.json'))
OUT = os.path.abspath(sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(SRC), 'index.html'))
with open(SRC, encoding='utf-8') as stream:
    data = json.load(stream)
DATA_JS = script_json(data)


TMAP_KEY, _ = load_tmap_key()
if not TMAP_KEY:
    sys.stderr.write('ERROR: 未找到腾讯地图 Key（~/.tencentmap/tempkey.json）。先跑 check_deps.py。\n')
    sys.exit(2)


def _qdate(*keys):
    """查询日期取自 JSON 的 source 字段，不写死。取不到再退到 meta.updatedAt。"""
    src = data.get('source') or {}
    for k in keys:
        v = str(src.get(k) or '').strip()
        if v:
            return v[:10]
    v = str((data.get('meta') or {}).get('updatedAt') or '').strip()
    return v[:10] if v else '未标注'


TRIP_Q = _qdate('tripQueryAt', 'mapQueryAt')
MAP_Q = _qdate('mapQueryAt', 'tripQueryAt')


def slug(name):
    h = hashlib.md5((name or 'city').encode('utf-8')).hexdigest()[:6]
    return 'c' + h


def derive_stops(trip):
    """从 days[].mapPoints 推导城市节点；没有点位的城市跳过。"""
    origin = (trip.get('meta') or {}).get('origin') or ''
    stops = []
    seen = set()
    if origin:
        # 起点没有 mapPoints 时，不硬编坐标；全线图从第一座有点位的城市开始
        pass
    for d in trip.get('days') or []:
        city = d.get('city') or ''
        if not city or city in seen:
            continue
        pts = [p for p in (d.get('mapPoints') or []) if isinstance(p.get('lat'), (int, float)) and isinstance(p.get('lng'), (int, float))]
        if not pts:
            continue
        seen.add(city)
        lat = sum(p['lat'] for p in pts) / len(pts)
        lng = sum(p['lng'] for p in pts) / len(pts)
        key = slug(city)
        stops.append({"name": city, "lat": round(lat, 6), "lng": round(lng, 6), "view": key})
    views = [{"key": "all", "label": "全线", "center": [43.5, 125.0], "zoom": 4}]
    if stops:
        avg_lat = sum(s['lat'] for s in stops) / len(stops)
        avg_lng = sum(s['lng'] for s in stops) / len(stops)
        views[0]['center'] = [round(avg_lat, 4), round(avg_lng, 4)]
        views[0]['zoom'] = 5 if len(stops) >= 3 else 7
    for s in stops:
        views.append({"key": s['view'], "label": s['name'], "center": [s['lat'], s['lng']], "zoom": 12})
    return stops, views


CITY_STOPS, CITY_VIEWS = derive_stops(data)
VIEW_STOPS_JS = script_json(CITY_STOPS)
VIEWS_JS = script_json(CITY_VIEWS)

TPL = r'''<!DOCTYPE html>
<!--
  ============================================================================
  这份 HTML 的数据 100% 内嵌在下方 <script id="TRIP_DATA"> 里，内容与同目录的
  travel-data.json 解析后的数据一致（嵌入时做 HTML 安全转义）。
  想拆成外部数据文件：把 <script id="TRIP_DATA" type="application/json"> 里的
  内容原样另存为 travel-data.json，再把该标签替换为 fetch('./travel-data.json')
  并在 DOMContentLoaded 后渲染即可，其余渲染代码无需改动。
  ============================================================================
-->
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title></title>
<style>
  :root{
    --bg:#f5f3ee; --card:#ffffff; --ink:#1f1d1a; --ink2:#5c574f; --ink3:#8b857b;
    --line:#e8e3d9; --brand:#c8452c; --brand2:#2f6bff; --food:#e8833a;
    --ref:#f7f4ea; --refink:#7a6f57; --ok:#2f8f5b;
    --r:18px;
  }
  *{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
  html,body{margin:0;padding:0;background:var(--bg);color:var(--ink);
    font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
    font-size:15px;line-height:1.55;-webkit-font-smoothing:antialiased}
  .wrap{max-width:480px;margin:0 auto;padding:14px 14px 92px}
  /* header */
  .hero{background:linear-gradient(160deg,#1f1d1a,#3a352e);color:#fff;border-radius:22px;padding:16px 18px 14px;margin-bottom:12px}
  .hero h1{margin:0 0 4px;font-size:19px;letter-spacing:.2px;font-weight:700}
  .hero p{margin:0;font-size:12.5px;color:#cfc8ba}
  .cd{margin-top:12px;background:rgba(255,255,255,.1);border-radius:14px;padding:10px 12px;display:block}
  .cd b{font-size:21px;font-weight:700;letter-spacing:.5px;white-space:nowrap;display:block;margin-top:1px}
  .cd span{font-size:12px;color:#cfc8ba;display:block;margin-top:4px;line-height:1.5}
  .cd .cdl{font-size:11.5px;color:#a89f8f;margin:0}
  /* tabs */
  .tabs{position:fixed;left:0;right:0;bottom:0;z-index:20;background:rgba(255,255,255,.94);
    backdrop-filter:blur(12px);border-top:1px solid var(--line);display:flex;justify-content:center;
    padding:6px 4px calc(6px + env(safe-area-inset-bottom))}
  .tabs .tb{flex:1;text-align:center;font-size:11px;color:var(--ink3);padding:6px 0 4px;border:0;background:none;font-family:inherit;cursor:pointer}
  .tabs .tb svg{display:block;margin:0 auto 2px;opacity:.5}
  .tabs .tb.on{color:var(--brand);font-weight:600}
  /* Tab 图标统一用内联 SVG：emoji 在不同系统/浏览器会渲染成带日期数字的图标（如日历显示 17），
     跨设备不一致且容易被误读成角标，故一律不用 emoji。 */
  .tabs .tb.on svg{opacity:1}
  .tabs-inner{max-width:480px;margin:0 auto;display:flex;width:100%}
  /* generic card */
  .card{background:var(--card);border-radius:var(--r);padding:14px 15px;margin-bottom:11px;box-shadow:0 1px 2px rgba(31,29,26,.05)}
  .card h2{margin:0 0 10px;font-size:15px;font-weight:700;display:flex;align-items:center;gap:7px}
  .card h2::before{content:"";width:3px;height:14px;border-radius:2px;background:var(--brand)}
  .sub{font-size:12px;color:var(--ink3);margin:-4px 0 10px}
  .muted{color:var(--ink3)}
  /* badges */
  .b{display:inline-block;font-size:10px;padding:1px 6px;border-radius:6px;vertical-align:1px;font-weight:600;line-height:1.6}
  .b-real{background:#e9f5ee;color:var(--ok)}
  .b-est{background:#fdf0e6;color:#b5651d}
  .b-ref{background:var(--ref);color:var(--refink)}
  .b-na{background:#efedE8;color:#8b857b}
  .b-gray{background:#eef1f7;color:#4a5878}
  /* rows */
  .row{display:flex;gap:10px;padding:9px 0;border-bottom:1px dashed var(--line)}
  .row:last-child{border-bottom:0}
  .row .k{flex:1;min-width:0}
  .row .v{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
  .t1{font-size:14px;font-weight:600}
  .t2{font-size:12px;color:var(--ink2)}
  .t3{font-size:11.5px;color:var(--ink3)}
  .price{color:var(--brand);font-weight:700}
  /* day card */
  .day{padding:0;overflow:hidden}
  .day > .hd{display:flex;align-items:center;gap:10px;padding:13px 15px;cursor:pointer;user-select:none}
  .day .dt{flex:0 0 auto;text-align:center;background:#f3efe6;border-radius:12px;padding:5px 9px;min-width:52px}
  .day .dt b{display:block;font-size:15px;font-weight:700;line-height:1.15}
  .day .dt span{font-size:10px;color:var(--ink3)}
  .day .tt{flex:1;min-width:0}
  .day .tt b{font-size:14px;font-weight:600;display:block}
  .day .tt span{font-size:11.5px;color:var(--ink3)}
  .day .cv{flex:0 0 auto;color:var(--ink3);font-size:12px;transition:transform .2s}
  .day.open .cv{transform:rotate(180deg)}
  .day .bd{display:none;padding:0 15px 14px;border-top:1px solid var(--line)}
  .day.open .bd{display:block}
  .slot{display:flex;gap:9px;padding:9px 0 0}
  .slot .lb{flex:0 0 40px;font-size:11px;color:#fff;background:var(--ink3);border-radius:7px;text-align:center;height:19px;line-height:19px;margin-top:2px}
  .slot.am .lb{background:#4b7bd6}.slot.pm .lb{background:#c98a2e}.slot.ev .lb{background:#5a4a7a}
  .slot .tx{flex:1;font-size:13px;color:var(--ink2)}
  .blk{margin-top:11px;border-radius:13px;overflow:hidden}
  .blk .bt{font-size:11.5px;font-weight:700;color:var(--ink2);padding:0 0 6px}
  .ref{background:var(--ref);border-radius:12px;padding:9px 11px;margin-top:7px}
  .ref .rt{font-size:12.5px;font-weight:600;color:var(--refink)}
  .ref .rl{font-size:12px;color:#6d6349;margin-top:2px}
  .warn{background:#fdf3f1;border-left:3px solid var(--brand);border-radius:0 11px 11px 0;padding:8px 11px;margin-top:8px;font-size:12.5px;color:#7a3a2e}
  .hotel{background:#f4f7fd;border-radius:12px;padding:10px 11px;margin-top:9px}
  .hotel .hn{font-size:13.5px;font-weight:600;color:#2b3f6b}
  .hotel .hi{font-size:12px;color:#4a5878;margin-top:3px}
  /* food */
  .fgrp{margin-bottom:12px}
  .fgrp .fh{font-size:13px;font-weight:700;margin:0 0 7px;display:flex;justify-content:space-between;align-items:baseline}
  .fd{display:flex;gap:10px;padding:5px 0;border-top:1px dashed var(--line)}
  .fd:first-of-type{border-top:0}
  .fd .fn{font-weight:600;font-size:13.5px;cursor:pointer}
  .fd .fn:hover{color:var(--brand)}
  .fd .fl{font-size:11.5px;color:var(--ink3);margin-top:1px}
  .fd .fr{text-align:right;white-space:nowrap}
  /* map */
  #mapbox{position:relative;height:300px;border-radius:15px;overflow:hidden;background:#eae7e0;margin-bottom:10px}
  #mapbox .fb{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:18px;font-size:12.5px;color:var(--ink2);gap:6px}
  .pills{display:flex;gap:6px;overflow-x:auto;padding-bottom:9px;-webkit-overflow-scrolling:touch;scrollbar-width:none}
  .pills::-webkit-scrollbar{display:none}
  .pill{flex:0 0 auto;border:1px solid var(--line);background:#fff;color:var(--ink2);border-radius:999px;
    padding:5px 12px;font-size:12px;font-family:inherit;cursor:pointer;white-space:nowrap}
  .pill.on{background:var(--ink);border-color:var(--ink);color:#fff;font-weight:600}
  .lgd{display:flex;gap:14px;font-size:11.5px;color:var(--ink3);margin-bottom:8px}
  .lgd i{display:inline-block;width:9px;height:9px;border-radius:3px;margin-right:4px;vertical-align:0}
  /* todo / ticket */
  .ck{display:flex;gap:10px;align-items:flex-start;padding:8px 0;border-bottom:1px dashed var(--line);font-size:13.5px}
  .ck:last-child{border-bottom:0}
  .ck input{width:18px;height:18px;margin:1px 0 0;accent-color:var(--brand);flex:0 0 auto}
  .ck.done .lb{text-decoration:line-through;color:var(--ink3)}
  .ptag{font-size:10px;padding:1px 5px;border-radius:5px;background:#eef1f7;color:#4a5878;font-weight:700;margin-right:5px}
  .ptag.P0{background:#fdeceb;color:#b83a2a}
  .lrow{font-size:12.5px;color:var(--ink2);padding:6px 0;border-top:1px dashed var(--line);display:flex;justify-content:space-between;gap:10px}
  .lrow:first-of-type{border-top:0}
  .sum{display:flex;justify-content:space-between;font-size:13px;font-weight:700;padding-top:9px;border-top:1px solid var(--line);margin-top:4px}
  footer{font-size:11.5px;color:var(--ink3);text-align:center;padding:8px 6px 0;line-height:1.7}
  .hidden{display:none}
</style>
</head>
<body>
<div class="wrap">
  <div class="hero">
    <h1 id="hTitle"></h1>
    <p id="hSub"></p>
    <div class="cd">
      <div><span class="cdl" id="cdLabel">距离最近一程出发</span><b id="cdNum">--</b></div>
      <span id="cdWhat"></span>
    </div>
  </div>
  <div id="panes"></div>
  <footer>
    价格与班次来自同程旅行实查（__TRIP_Q__）；坐标 / 营业时间 / 人均来自腾讯地图实查（__MAP_Q__）。<br>
    标注【参考】的机位、最佳时段与必吃菜为攻略类检索信息，会因季节、施工、人流、灯光时间变化，请以现场为准。<br>
    内置地图由腾讯地图提供。此页面含地图访问凭据，仅供本地或受信任的内网预览，请勿上传至公开仓库。
  </footer>
</div>

<nav class="tabs"><div class="tabs-inner" id="tabbar"></div></nav>

<script id="TRIP_DATA" type="application/json">@@DATA@@</script>
<script>
window.__CITY_STOPS__ = @@STOPS@@;
window.__CITY_VIEWS__ = @@VIEWS@@;
</script>
<script>
/* ===== 数据 ===== */
var TRIP = JSON.parse(document.getElementById('TRIP_DATA').textContent);
window.TRIP = TRIP;
var CITY_STOPS = window.__CITY_STOPS__;
var CITY_VIEWS = window.__CITY_VIEWS__;
var MAP_QUERY = @@MAP_QUERY@@;

/* ===== 工具 ===== */
function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
function ptype(t){
  /* 默认态不标：实查数据直接展示数值即可，冗余的「实」标签反而干扰阅读。
     只标异常态：估（推算）与未查到。参考类信息另走「参考」标记。 */
  if(t==='实') return '';
  if(t==='估') return '<span class="b b-est">估</span>';
  return '<span class="b b-na">未查到</span>';
}
function money(v){
  if(v===0) return '<span class="price">免费</span>';
  if(typeof v!=='number') return '<span class="muted">未查到</span>';
  return '<span class="price">¥'+v.toLocaleString('zh-CN')+'</span>';
}
function ymd(d){var s=String(d).split('-');return {m:+s[1],d:+s[2]};}
var WEEK=['日','一','二','三','四','五','六'];
function weekOf(ds){var t=new Date(ds+'T00:00:00');return '周'+WEEK[t.getDay()];}
function toDate(ds,hm){return new Date(ds+'T'+(hm&&hm.length===5?hm:'00:00')+':00');}

/* ===== 最近一程倒计时 ===== */
function nearestLeg(){
  var now=new Date(), best=null;
  (TRIP.flightsOrTrains||[]).forEach(function(f){
    var t=toDate(f.date,f.depart);
    if(t>now && (!best || t<best.t)) best={t:t,f:f};
  });
  return best;
}
function renderCountdown(){
  var b=nearestLeg(), num=document.getElementById('cdNum'), what=document.getElementById('cdWhat');
  if(!b){num.textContent='已出发';what.textContent='';return;}
  var ms=b.t-new Date(), d=Math.floor(ms/86400000), h=Math.floor(ms%86400000/3600000);
  num.textContent=(d>0? d+' 天 ':'')+h+' 小时';
  var y=ymd(b.f.date);
  what.textContent='· '+y.m+'/'+y.d+' '+(b.f.no||'')+' '+b.f.from+' → '+b.f.to+' '+b.f.depart;
}

/* ===== Tab ===== */
var ICO='fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"';
function ic(d){return '<svg viewBox="0 0 18 18" width="18" height="18" '+ICO+'>'+d+'</svg>';}
var TABS=[
  {k:'traffic',i:ic('<path d="M2.6 11.4h6.2M8.8 11.4 14 6.2M8.8 11.4l5.2 5.2M3.6 5.4h3.6"/>'),l:'交通'},
  {k:'route',i:ic('<path d="M9 15.6s4.6-4.7 4.6-7.7A4.6 4.6 0 0 0 4.4 7.9c0 3 4.6 7.7 4.6 7.7z"/><circle cx="9" cy="7.7" r="1.5"/>'),l:'路线'},
  {k:'plan',i:ic('<rect x="2.6" y="3.8" width="12.8" height="11.6" rx="2.2"/><path d="M2.6 7.3h12.8M6 2.4v2.8M12 2.4v2.8"/>'),l:'行程'},
  {k:'ticket',i:ic('<path d="M2.4 6.4h13.2v1.6a1.6 1.6 0 0 0 0 3.2v1.6H2.4v-1.6a1.6 1.6 0 0 0 0-3.2V6.4z"/><path d="M8.9 5.2v7.6"/>'),l:'门票'},
  {k:'food',i:ic('<path d="M3.2 8.6h11.6a5.8 5.8 0 0 1-11.6 0z"/><path d="M6.4 5.4c0-1.1 1.1-1.1 1.1-2.2M9.9 5.4c0-1.1 1.1-1.1 1.1-2.2"/>'),l:'吃'},
  {k:'todo',i:ic('<rect x="2.6" y="2.6" width="12.8" height="12.8" rx="2.8"/><path d="M5.8 9.2 8.1 11.4 12.4 6.9"/>'),l:'Todo'}
];
var active='traffic', mapInited=false;
function buildTabs(){
  var bar=document.getElementById('tabbar');
  TABS.forEach(function(t){
    var b=document.createElement('button');
    b.className='tb'+(t.k===active?' on':''); b.dataset.k=t.k;
    b.innerHTML=t.i+t.l;
    b.onclick=function(){switchTab(t.k);};
    bar.appendChild(b);
  });
}
function switchTab(k){
  active=k;
  Array.prototype.forEach.call(document.querySelectorAll('.tb'),function(b){b.classList.toggle('on',b.dataset.k===k);});
  Array.prototype.forEach.call(document.querySelectorAll('.pane'),function(p){p.classList.toggle('hidden',p.dataset.k!==k);});
  window.scrollTo({top:0,behavior:'smooth'});
  if(k==='route'){ setTimeout(ensureMap,80); }
}

/* ===== 渲染各 Tab ===== */
function renderTraffic(){
  var people=(TRIP.meta&&TRIP.meta.people)||2;
  var queried=(TRIP.source&&TRIP.source.tripQueryAt)||(TRIP.meta&&TRIP.meta.updatedAt)||'';
  var h=['<div class="card"><h2>交通比选'+(queried?'（实查 · '+esc(queried)+'）':'')+'</h2>'];
  h.push('<div class="sub">价格为单人票价。主方案由方案文案给出，本页列出全部实查班次。</div>');
  var sum=0, n=0;
  (TRIP.flightsOrTrains||[]).forEach(function(f){
    var y=ymd(f.date);
    var mode=f.mode==='flight'?'✈️':'🚄';
    if(typeof f.price==='number'){ sum+=f.price; n+=1; }
    h.push('<div class="row"><div class="k">'
      +'<div class="t1">'+mode+' '+esc(f.no)+'</div>'
      +'<div class="t2">'+esc(f.from)+' → '+esc(f.to)+'</div>'
      +'<div class="t3">'+y.m+'月'+y.d+'日 '+weekOf(f.date)+' · '+esc(f.depart)+'-'+esc(f.arrive)+' · '+esc(f.duration)+'</div>'
      +(f.note?'<div class="t3" style="color:#8b857b;margin-top:3px">'+esc(f.note)+'</div>':'')
      +'</div><div class="v"><div>'+money(f.price)+' '+ptype(f.priceType)+'</div><div class="t3">'+esc(people)+'人 '+money(typeof f.price==='number'?f.price*people:null)+'</div></div></div>');
  });
  if(n) h.push('<div class="sum"><span>上表票价加总（'+esc(people)+' 人，含备选班次）</span><span class="price">¥'+(sum*people).toLocaleString('zh-CN')+'</span></div>');
  h.push('</div>');
  return h.join('');
}

function renderRoute(){
  var h=['<div class="card"><h2>路线 · 内置地图</h2>'];
  h.push('<div class="pills" id="viewPills"></div>');
  h.push('<div class="lgd"><span><i style="background:#2f6bff"></i>景点</span><span><i style="background:#e8833a"></i>美食</span><span><i style="background:#c8452c"></i>城市节点</span></div>');
  h.push('<div id="mapbox"><div class="fb" id="mapFallback"><div>地图加载中…</div></div></div>');
  h.push('<div class="sub" style="margin:8px 0 0">全线视图画城市节点与走向连线；切到城市视图只看该城点位。坐标系 GCJ-02。</div>');
  h.push('</div>');
  /* 城市小结：按 days 顺序，每天标题拼成该城顺序 */
  h.push('<div class="card"><h2>同城顺序建议</h2>');
  var byCity={}, cityOrder=[];
  (TRIP.days||[]).forEach(function(d,i){
    var c=d.city||'';
    if(!c) return;
    if(!byCity[c]){ byCity[c]=[]; cityOrder.push(c); }
    byCity[c].push('D'+(i+1)+' '+ (d.title||''));
  });
  cityOrder.forEach(function(c){
    h.push('<div class="row"><div class="k"><div class="t1">'+esc(c)+'</div><div class="t3">'+esc(byCity[c].join(' → '))+'</div></div></div>');
  });
  h.push('</div>');
  return h.join('');
}

function renderPlan(){
  var h=[];
  (TRIP.days||[]).forEach(function(d,i){
    var y=ymd(d.date);
    h.push('<div class="card day'+(i===0?' open':'')+'" data-day="'+i+'">');
    h.push('<div class="hd"><div class="dt"><b>D'+(i+1)+'</b><span>'+y.m+'/'+y.d+'</span></div>'
      +'<div class="tt"><b>'+esc(d.title)+'</b><span>'+esc(d.city)+' · '+weekOf(d.date)+'</span></div>'
      +'<div class="cv">▾</div></div>');
    h.push('<div class="bd">');
    h.push('<div class="slot am"><div class="lb">上午</div><div class="tx">'+esc(d.am)+'</div></div>');
    h.push('<div class="slot pm"><div class="lb">下午</div><div class="tx">'+esc(d.pm)+'</div></div>');
    h.push('<div class="slot ev"><div class="lb">晚上</div><div class="tx">'+esc(d.evening)+'</div></div>');
    /* 出片（经验信息，浅底 + 参考） */
    if(d.photoSpots && d.photoSpots.length){
      h.push('<div class="blk"><div class="bt">出片攻略 <span class="b b-ref">参考</span></div>');
      d.photoSpots.forEach(function(p){
        h.push('<div class="ref"><div class="rt">'+esc(p.name)+' · '+esc(p.shot)+'</div>'
          +'<div class="rl">最佳时段：'+esc(p.bestTime)+'</div>'
          +'<div class="rl">拍摄要点：'+esc(p.tip)+'</div>'
          +'<div class="rl">到达：'+esc(p.traffic)+'</div>'
          +'<div class="rl" style="color:#8b857b">来源：'+esc(p.source)+'｜'+esc(p.confidence)+'</div></div>');
      });
      h.push('</div>');
    }
    /* 吃（本日动线） */
    if(d.foods && d.foods.length){
      h.push('<div class="blk"><div class="bt">本日吃什么</div>');
      d.foods.forEach(function(f){
        h.push('<div class="row"><div class="k"><div class="t1">'+esc(f.name)+'</div>'
          +'<div class="t3">'+esc(f.dish)+' · '+esc(f.area)+'</div>'
          +'<div class="t3">营业 '+esc(f.openHours)+' · 评分 '+esc(f.score)+'</div></div>'
          +'<div class="v">'+(typeof f.avgPrice==='number'? money(f.avgPrice):'<span class="muted">人均未查到</span>')
          +'<div class="t3">人均</div></div></div>');
      });
      h.push('</div>');
    }
    (d.warnings||[]).forEach(function(w){ h.push('<div class="warn">'+esc(w)+'</div>'); });
    h.push('</div></div>');
  });
  return h.join('');
}

function renderTickets(){
  var h=['<div class="card"><h2>门票 / 预约</h2><div class="sub">勾选状态保存在本机浏览器。</div>'];
  var any=false;
  (TRIP.days||[]).forEach(function(d){
    if(!d.tickets || !d.tickets.length) return;
    any=true;
    h.push('<div class="t3" style="margin:10px 0 2px;font-weight:700;color:#5c574f">'+esc(d.date)+' · '+esc(d.city)+'</div>');
    d.tickets.forEach(function(t,idx){
      var id='tk_'+d.date+'_'+idx;
      h.push('<label class="ck" data-id="'+esc(id)+'"><input type="checkbox" data-ck="'+esc(id)+'">'
        +'<div class="lb"><b>'+esc(t.name)+'</b> '+money(t.price)+' '+ptype(t.priceType)
        +'<div class="t3" style="margin-top:3px">'+esc(t.note)+'</div></div></label>');
    });
  });
  if(!any) h.push('<div class="t3">暂无门票或预约记录，请按实际行程核对。</div>');
  h.push('</div>');
  return h.join('');
}

function renderFood(){
  var g={}, order=[];
  (TRIP.days||[]).forEach(function(d){
    (d.foods||[]).forEach(function(f){
      if(!g[d.city]){g[d.city]=[];order.push(d.city);}
      g[d.city].push(f);
    });
  });
  var h=['<div class="card"><h2>吃 · 按城市</h2><div class="sub">人均来自腾讯地图实查（'+esc(MAP_QUERY)+'）；菜名为地域经验，标【参考】。点店名可跳到地图对应城市视图。</div>'];
  order.forEach(function(c){
    h.push('<div class="fgrp"><div class="fh"><span>'+esc(c)+'</span><span class="t3">'+g[c].length+' 家</span></div>');
    g[c].forEach(function(f){
      h.push('<div class="fd"><div style="flex:1;min-width:0">'
        +'<div class="fn" data-jump="'+esc(f.lat)+','+esc(f.lng)+'">'+esc(f.name)+' <span class="b b-ref">参考</span></div>'
        +'<div class="fl">'+esc(f.dish)+' · '+esc(f.area)+'</div>'
        +'<div class="fl">营业 '+esc(f.openHours)+' · 评分 '+esc(f.score)+'</div>'
        +'</div><div class="fr">'+(typeof f.avgPrice==='number'? money(f.avgPrice):'<span class="muted">未查到</span>')
        +'<div class="t3">'+(typeof f.avgPrice==='number'? ptype(f.priceType):'')+'</div></div></div>');
    });
    h.push('</div>');
  });
  h.push('</div>');
  return h.join('');
}

function renderTodo(){
  var h=['<div class="card"><h2>行前 Todo</h2>'];
  (TRIP.todos||[]).forEach(function(t,i){
    var id='td_'+i;
    h.push('<label class="ck" data-id="'+id+'"><input type="checkbox" data-ck="'+id+'">'
      +'<div class="lb"><span class="ptag '+esc(t.priority)+'">'+esc(t.priority)+'</span>'+esc(t.text)+'</div></label>');
  });
  h.push('</div>');
  /* 预算 */
  h.push('<div class="card"><h2>预算两档（'+esc(TRIP.meta.people)+' 人合计）</h2>');
  ['comfort','saver'].forEach(function(k){
    var b=(TRIP.budget||{})[k];
    if(!b) return;
    h.push('<div class="t1" style="margin:6px 0 4px">'+esc(b.title)+'</div>');
    Object.keys(b.items||{}).forEach(function(key){
      h.push('<div class="lrow"><span>'+esc(key)+'</span><span>'+money(b.items[key])+'</span></div>');
    });
    h.push('<div class="sum"><span>合计 · 人均</span><span>'+money(b.total)+' · 人均 '+money(b.perPerson)+'</span></div>');
    h.push('<div class="t3" style="margin:6px 0 12px">'+esc(b.note)+'</div>');
  });
  h.push('</div>');
  return h.join('');
}

/* ===== localStorage 勾选 ===== */
function bindChecks(){
  Array.prototype.forEach.call(document.querySelectorAll('input[data-ck]'),function(el){
    var id=el.dataset.ck;
    var on=false;
    try{ on=localStorage.getItem('trip_'+id)==='1'; }catch(e){}
    el.checked=on;
    el.closest('.ck').classList.toggle('done',on);
    el.addEventListener('change',function(){
      el.closest('.ck').classList.toggle('done',el.checked);
      try{ localStorage.setItem('trip_'+id, el.checked?'1':'0'); }catch(e){}
    });
  });
}

/* ===== 地图 ===== */
var map=null, markerLayer=null, lineLayer=null, curView='all';
var _tmState=0, _tmWait=[];
/* 懒加载腾讯 GL JS：切到「路线」页才注入 SDK，避免首屏被地图拖慢。
   Key 明文内嵌，仅用于本地或受信任的内网预览。
   公网部署前应按腾讯地图官方文档设置代理与访问限制。 */
function ensureMap(){
  if(mapInited) return;
  if(typeof TMap!=='undefined' && TMap.Map){ initMap(); return; }
  if(_tmState===2){ return; }
  if(_tmState===1){ _tmWait.push(initMap); return; }
  _tmState=1;
  _tmWait.push(initMap);
  var s=document.createElement('script');
  s.src='https://map.qq.com/api/gljs?v=1&key=@@TMAPKEY@@';
  s.async=true;
  s.onload=function(){
    _tmState=3;
    var a=_tmWait.slice(); _tmWait=[];
    a.forEach(function(f){ try{ f(); }catch(e){ console.warn(e); } });
  };
  s.onerror=function(){
    _tmState=2; _tmWait=[];
    mapFallback('地图 SDK 加载失败（网络或代理未就绪）。');
  };
  document.head.appendChild(s);
}
function pin(color){
  var svg='<svg xmlns="http://www.w3.org/2000/svg" width="26" height="34" viewBox="0 0 26 34">'
    +'<path d="M13 0C5.8 0 0 5.8 0 13c0 9.7 13 21 13 21s13-11.3 13-21C26 5.8 20.2 0 13 0z" fill="'+color+'"/>'
    +'<circle cx="13" cy="13" r="5.2" fill="#fff"/></svg>';
  return 'data:image/svg+xml;charset=utf-8,'+encodeURIComponent(svg);
}
function viewCity(key){ // 归组：把每天的 mapPoints 归到城市
  return key;
}
function pointsFor(view){
  var out=[];
  if(view==='all') return out;
  var stop=CITY_STOPS.filter(function(c){return c.view===view;})[0];
  var target=stop?stop.name:null;
  if(!target) return out;
  (TRIP.days||[]).forEach(function(d){
    if(d.city!==target) return;
    (d.mapPoints||[]).forEach(function(p){
      out.push({id:view+'_'+out.length,lat:p.lat,lng:p.lng,name:p.name,kind:p.kind,hours:p.openHours});
    });
  });
  return out;
}
function cityGeoms(){
  return CITY_STOPS.map(function(c,i){
    return {id:'city_'+i, styleId:'city', position:new TMap.LatLng(c.lat,c.lng), properties:{title:c.name}};
  });
}
function applyView(view){
  curView=view;
  if(!map) return;
  var geoms=[];
  if(view==='all'){
    geoms=cityGeoms();
    if(lineLayer){ try{ lineLayer.setVisible(true);}catch(e){} }
  }else{
    if(lineLayer){ try{ lineLayer.setVisible(false);}catch(e){} }
    var pts=pointsFor(view);
    geoms=pts.map(function(p){
      return {id:p.id, styleId:(p.kind==='food'?'food':'sight'),
        position:new TMap.LatLng(p.lat,p.lng),
        properties:{title:p.name+'\n'+(p.hours&&p.hours!=='未查到'?('营业 '+p.hours):'营业时间未查到')}};
    });
  }
  if(markerLayer){ try{ markerLayer.setGeometries(geoms); }catch(e){ console.warn(e); } }
  var v=CITY_VIEWS.filter(function(x){return x.key===view;})[0];
  if(v){ map.setCenter(new TMap.LatLng(v.center[0],v.center[1])); map.setZoom(v.zoom); }
}
function buildPills(){
  var box=document.getElementById('viewPills');
  if(!box) return;
  box.innerHTML='';
  CITY_VIEWS.forEach(function(v){
    var b=document.createElement('button');
    b.className='pill'+(v.key===curView?' on':''); b.textContent=v.label; b.dataset.k=v.key;
    b.onclick=function(){
      Array.prototype.forEach.call(box.children,function(c){c.classList.toggle('on',c.dataset.k===v.key);});
      applyView(v.key);
    };
    box.appendChild(b);
  });
}
function mapFallback(msg){
  var f=document.getElementById('mapFallback');
  if(!f) return;
  f.innerHTML='<div style="font-weight:600">地图未能加载</div><div>'+esc(msg)+'</div>'
    +'<div class="t3">点位深链仍可用：下方「同城顺序建议」与「吃」页保留了全部地点信息。</div>';
  f.style.display='flex';
}
function initMap(){
  if(mapInited) return;
  var box=document.getElementById('mapbox');
  if(!box || box.offsetWidth===0) return;  // 仍在隐藏 Tab，等下一次
  mapInited=true;
  if(typeof TMap==='undefined' || !TMap.Map){ mapFallback('地图 SDK 不可达（网络或代理未就绪）。'); return; }
  try{
    map=new TMap.Map('mapbox',{center:new TMap.LatLng(43.5,125.0),zoom:4});
    var styles={
      sight:new TMap.MarkerStyle({width:26,height:34,anchor:{x:13,y:34},src:pin('#2f6bff')}),
      food:new TMap.MarkerStyle({width:26,height:34,anchor:{x:13,y:34},src:pin('#e8833a')}),
      city:new TMap.MarkerStyle({width:30,height:38,anchor:{x:15,y:38},src:pin('#c8452c')})
    };
    var geo=cityGeoms();
    markerLayer=new TMap.MultiMarker({
      map:map, styles:styles, geometries:geo
    });
    lineLayer=new TMap.MultiPolyline({
      map:map,
      styles:{route:new TMap.PolylineStyle({color:'#c8452c',width:3,borderWidth:1,borderColor:'#ffffff',lineCap:'round'})},
      geometries:[{id:'main',styleId:'route',
        paths:CITY_STOPS.map(function(c){return new TMap.LatLng(c.lat,c.lng);})}]
    });
    /* InfoWindow 必须带初始 position 创建，否则 SDK 内部 projectToContainer(undefined)
       返回 null 并在渲染时抛 "Cannot read properties of null (reading 'x')" */
    var info=new TMap.InfoWindow({map:map,position:new TMap.LatLng(43.5,125.0),offset:{x:0,y:-30},content:''});
    info.close();
    markerLayer.on('click',function(e){
      info.open();
      info.setPosition(e.geometry.position);
      info.setContent('<div style="font-size:12.5px;padding:2px 4px;white-space:pre-line">'+esc(e.geometry.properties.title||'')+'</div>');
    });
    var f=document.getElementById('mapFallback');
    if(f) f.style.display='none';
    buildPills();
    applyView(curView);
    setTimeout(function(){ map.setCenter(new TMap.LatLng(43.5,125.0)); map.setZoom(4); applyView('all'); },120);
  }catch(err){
    console.warn(err);
    mapFallback('地图初始化失败：'+(err&&err.message?err.message:err));
  }
  setTimeout(function(){
    if(!map) mapFallback('地图长时间未响应（SDK 或代理不可达）。');
  },4000);
}

/* ===== 启动 ===== */
function boot(){
  document.title=TRIP.meta.title;
  document.getElementById('hTitle').textContent=TRIP.meta.title;
  var m=TRIP.meta;
  document.getElementById('hSub').textContent=m.dateStart+' — '+m.dateEnd+' · '+m.days+' 天 · '+m.people+' 人 · '+m.destinations.join(' → ');
  buildTabs();
  document.getElementById('panes').innerHTML=
      '<div class="pane" data-k="traffic">'+renderTraffic()+'</div>'
    + '<div class="pane" data-k="route">'+renderRoute()+'</div>'
    + '<div class="pane" data-k="plan">'+renderPlan()+'</div>'
    + '<div class="pane" data-k="ticket">'+renderTickets()+'</div>'
    + '<div class="pane" data-k="food">'+renderFood()+'</div>'
    + '<div class="pane" data-k="todo">'+renderTodo()+'</div>';
  Array.prototype.forEach.call(document.querySelectorAll('.pane'),function(p){p.classList.toggle('hidden',p.dataset.k!==active);});
  /* 日卡折叠 */
  Array.prototype.forEach.call(document.querySelectorAll('.day .hd'),function(hd){
    hd.addEventListener('click',function(){ hd.parentNode.classList.toggle('open'); });
  });
  /* 吃 → 地图 */
  Array.prototype.forEach.call(document.querySelectorAll('.fn[data-jump]'),function(el){
    el.addEventListener('click',function(){
      switchTab('route');
      setTimeout(function(){
        var d=document.querySelector('.day'); // noop
        var target=nearestCityView(parseFloat(el.dataset.jump.split(',')[0]),parseFloat(el.dataset.jump.split(',')[1]));
        if(target){
          var box=document.getElementById('viewPills');
          if(box) Array.prototype.forEach.call(box.children,function(c){c.classList.toggle('on',c.dataset.k===target);});
          curView=target; setTimeout(function(){ ensureMap(); setTimeout(function(){ if(map) applyView(target); },160); },100);
        }
      },100);
    });
  });
  bindChecks();
  renderCountdown();
  setInterval(renderCountdown,60000);
  if(active==='route') setTimeout(ensureMap,80);
}
function nearestCityView(lat,lng){
  var best=null,bd=1e9;
  CITY_STOPS.forEach(function(c){
    var d=Math.pow(c.lat-lat,2)+Math.pow(c.lng-lng,2);
    if(d<bd){bd=d;best=c.view;}
  });
  return best;
}
document.addEventListener('DOMContentLoaded',boot);
if(document.readyState!=='loading') boot();
</script>
</body>
</html>
'''

replacements = {
    '@@DATA@@': DATA_JS,
    '@@STOPS@@': VIEW_STOPS_JS,
    '@@VIEWS@@': VIEWS_JS,
    '__TRIP_Q__': escape(TRIP_Q),
    '__MAP_Q__': escape(MAP_Q),
    '@@MAP_QUERY@@': script_json(MAP_Q),
    '@@TMAPKEY@@': quote(TMAP_KEY, safe=''),
}
# 一次替换，避免用户文本里的占位符再次被替换，破坏原数据或带入 Key。
html = re.sub('|'.join(re.escape(k) for k in replacements),
              lambda match: replacements[match.group()], TPL)

with open(OUT, 'w', encoding='utf-8') as stream:
    stream.write(html)
print('written', OUT, len(html))
