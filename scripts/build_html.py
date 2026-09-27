# -*- coding: utf-8 -*-
"""读取 travel-data.json → 生成移动端单页 index.html（数据内嵌，同源）。

用法：
  python build_html.py <travel-data.json> [out.html]

城市节点 / 视图胶囊从 JSON 的 days[].mapPoints 推导，不写死某条线路。
默认生成不含 Key 的公开页面和 Markdown。--local-map 才读取本机 Key，仅限本地预览。
"""
import json, os, sys, hashlib, re, argparse, math
from html import escape
from check_deps import load_tmap_key
from trip_document import to_markdown, assert_no_credentials


def script_json(value):
    """JSON 字符串也会被 HTML 的 </script> 截断，必须在嵌入前转义。"""
    return (json.dumps(value, ensure_ascii=False, separators=(',', ':'))
            .replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e')
            .replace('\u2028', '\\u2028').replace('\u2029', '\\u2029'))

parser = argparse.ArgumentParser(description='松鼠旅行官 · 生成行程页与 ima 文档')
parser.add_argument('source', nargs='?', default='travel-data.json')
parser.add_argument('output', nargs='?')
parser.add_argument('--local-map', action='store_true', help='显式嵌入本机 Key，仅限本地使用')
parser.add_argument('--install-url', default='https://github.com/mrliang-github/liangxiao-travel/releases/latest',
                    help='发布前设为已核实的 1.2.0 或更新安装包链接')
args = parser.parse_args()
if not (args.install_url.startswith('https://github.com/mrliang-github/liangxiao-travel/')
        or args.install_url == './liangxiao-travel-1.2.0.zip'):
    parser.error('安装链接必须是本项目 GitHub 地址或本地配套安装包')
SRC = os.path.abspath(args.source)
OUT = os.path.abspath(args.output or os.path.join(os.path.dirname(SRC), 'index.html'))
with open(SRC, encoding='utf-8') as stream:
    data = json.load(stream)
assert_no_credentials(data)
DATA_JS = script_json(data)
MARKDOWN = to_markdown(data)


TMAP_KEY = load_tmap_key()[0] if args.local_map else ''
if args.local_map and not TMAP_KEY:
    sys.stderr.write('ERROR: 未找到腾讯地图 Key（~/.tencentmap/tempkey.json）。先跑 check_deps.py。\n')
    sys.exit(2)


def _qdate(key):
    """查询日期只取对应来源，不能用文档更新或另一个服务的日期补齐。"""
    src = data.get('source') or {}
    v = str(src.get(key) or '').strip()
    return v[:10] if v else '未标注'


TRIP_Q = _qdate('tripQueryAt')
MAP_Q = _qdate('mapQueryAt')


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
        pts = [p for p in (d.get('mapPoints') or []) if all(type(p.get(k)) in (int, float)
               and math.isfinite(p[k]) and abs(p[k]) <= limit for k, limit in [('lat', 90), ('lng', 180)])]
        if not pts:
            continue
        seen.add(city)
        lat = sum(p['lat'] for p in pts) / len(pts)
        lng = sum(p['lng'] for p in pts) / len(pts)
        key = slug(city)
        stops.append({"name": city, "lat": round(lat, 6), "lng": round(lng, 6), "view": key})
    views = [{"key": "all", "label": "全线", "center": [35.0, 105.0], "zoom": 4}]
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
<meta name="referrer" content="no-referrer">
<meta name="description" content="松鼠旅行官：安排行程、整理预算、记住待办。打开示例，在 WorkBuddy 制作自己的旅行手册。">
<title></title>
<style>
  :root{
    --bg:#f4f3ed; --card:#ffffff; --ink:#24382e; --ink2:#546256; --ink3:#69776b;
    --line:#e2e6dc; --brand:#a64420; --brand2:#2f6bff; --food:#e8833a;
    --ref:#f7f4ea; --refink:#7a6f57; --ok:#2f8f5b;
    --r:18px;
  }
  *{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
  html,body{margin:0;padding:0;background:var(--bg);color:var(--ink);
    font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
    font-size:15px;line-height:1.55;-webkit-font-smoothing:antialiased}
  .wrap{max-width:1080px;margin:0 auto;padding:24px 22px 104px}
  /* header */
  .hero{background:#244d3a;color:#fff;border-radius:24px;padding:28px;margin-bottom:18px;position:relative;overflow:hidden}
  .hero h1{margin:0 0 10px;font-size:30px;letter-spacing:-.5px;line-height:1.35;font-weight:700;max-width:760px}
  .hero p{margin:0;font-size:14px;color:#d6e3d8}
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
  .tabs-inner{max-width:760px;margin:0 auto;display:flex;width:100%}
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
  button,a,input,textarea{font:inherit}
  a{color:var(--brand);text-underline-offset:3px}
  button{cursor:pointer}
  button:focus-visible,a:focus-visible,textarea:focus-visible,.hd:focus-visible{outline:3px solid #dc9247;outline-offset:4px}
  .brandbar{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:22px}
  .brandlock{display:flex;align-items:center;gap:12px}
  .brandname{font-size:21px;font-weight:800;letter-spacing:1px}
  .brandnote{font-size:12px;color:var(--ink2)}
  .squirrel{width:48px;height:48px;flex-shrink:0}
  .btn{display:inline-flex;justify-content:center;align-items:center;gap:7px;min-height:44px;padding:10px 18px;border:1px solid var(--line);border-radius:12px;background:#fff;color:var(--ink);text-decoration:none;font-weight:600}
  .btn.primary{background:var(--brand);color:#fff;border-color:var(--brand)}
  .btn.soft{background:#eff4ee}
  .actions{display:flex;gap:10px;flex-wrap:wrap}
  .eyebrow{font-size:12px;letter-spacing:2px;color:#d4deaa;margin-bottom:10px}
  .stats{display:flex;gap:24px;margin-top:22px;padding-top:18px;border-top:1px solid #ffffff28;flex-wrap:wrap}
  .stats b{font-size:24px;color:#fff;display:block}
  .stats span{font-size:12px;color:#d6e3d8}
  .cd{margin-top:18px;max-width:480px}
  .notice{border:1px solid #e1c895;border-radius:12px;background:#fff8e7;color:#735424;padding:10px 14px;margin-bottom:16px;font-size:12px}
  .pane[data-k="plan"]:not(.hidden){display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;align-items:start}
  .day{margin-bottom:0}
  .day > .hd{min-height:76px}
  .card h2{font-size:17px}
  .card{padding:18px}
  .day{padding:0}
  .section-intro{grid-column:1/-1;display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:2px}
  .section-intro h2{font-size:20px;margin:0}
  .section-intro p{font-size:12px;color:var(--ink2);margin:4px 0}
  .trip-note{font-size:13px;color:var(--ink2);margin:0 0 16px;overflow-wrap:anywhere}
  .route-order{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0}
  .route-stop{border:1px solid var(--line);border-radius:10px;background:#f4f7ef;padding:9px 12px;font-size:13px}
  #mapbox{height:340px}
  #mapbox .fb{background:#edf1e6;position:absolute}
  #mapFallback svg{width:100%;height:225px;flex:1;min-height:0}
  dialog{width:min(640px,calc(100% - 24px));max-height:88vh;border:0;border-radius:22px;padding:0;color:var(--ink);box-shadow:0 20px 90px #10261944}
  dialog::backdrop{background:#18312688;backdrop-filter:blur(4px)}
  .dialog-head{position:sticky;top:0;z-index:1;background:#fff;padding:18px 22px;border-bottom:1px solid var(--line);display:flex;align-items:center;justify-content:space-between;gap:12px}
  .dialog-head h2{font-size:20px;margin:0}
  .dialog-body{padding:20px 22px}
  .close{background:#f2f4ef;border:0;border-radius:50%;width:36px;height:36px;flex-shrink:0}
  .mode-switch{display:flex;gap:8px;margin-bottom:18px}
  .mode-switch button{flex:1}
  .mode-switch [aria-pressed="true"]{background:#244d3a;color:#fff;border-color:#244d3a}
  .setup-step{border:1px solid var(--line);border-radius:14px;padding:16px;margin-bottom:12px}
  .setup-step h3{font-size:16px;margin:0 0 8px}
  .setup-step p,.dialog-body li{font-size:13px;color:var(--ink2);line-height:1.8}
  .setup-step ol{padding-left:20px}
  .prompt{width:100%;min-height:178px;resize:vertical;padding:12px;border:1px solid var(--line);border-radius:10px;background:#f8f9f5;color:var(--ink);font-size:13px;line-height:1.8;margin-bottom:10px}
  .feedback{font-size:12px;color:var(--ok);min-height:22px;margin:6px 0}
  .muted-link{font-size:12px}
  @media(max-width:600px){
    .wrap{padding:14px 14px 96px}.brandbar{margin-bottom:16px;align-items:center}.brandlock{gap:8px}
    .squirrel{width:38px;height:38px}.brandname{font-size:18px}.brandnote{font-size:10px}.brandbar .btn{font-size:12px;padding:9px 11px}
    .hero{padding:22px 18px;border-radius:19px}.hero h1{font-size:24px}.hero p{font-size:12px}.stats{gap:22px}.stats b{font-size:23px}
    .pane[data-k="plan"]:not(.hidden){grid-template-columns:1fr}.section-intro{align-items:start}.section-intro h2{font-size:18px}
    .section-intro .btn{font-size:12px;padding:7px 10px}.dialog-body{padding:16px}.dialog-head{padding:16px}.card{padding:15px}.day{padding:0}
    #mapbox{height:290px}.row .v{white-space:normal;max-width:36%;min-width:70px}.lrow{flex-wrap:wrap}
  }
  @media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important;transition:none!important}}
</style>
</head>
<body>
<div class="wrap">
  <header class="brandbar">
    <div class="brandlock">
      <svg class="squirrel" viewBox="0 0 64 64" aria-hidden="true"><rect width="64" height="64" rx="18" fill="#f0e4c9"/><path d="M31 49C11 50 6 39 13 28c4-6 11-7 15-3 5 5 2 12-4 11 3 8 11 3 11-2" fill="none" stroke="#bc6d32" stroke-width="9" stroke-linecap="round"/><path d="M34 29l-1-15 9 9 8-7 1 16c10 14-1 22-12 20-10-2-12-13-5-23" fill="#b55e2e"/><path d="M42 34c-6 2-8 9-4 15 7 2 13-1 14-6" fill="#f5d8a7"/><circle cx="44" cy="29" r="2" fill="#24382e"/><path d="M49 35l5-1-3 4" fill="#24382e"/><path d="M37 41l7-2 5 7-8 6z" fill="#5e774c"/><path d="M39 42l6 6" stroke="#e4edcb" stroke-width="2"/></svg>
      <div><div class="brandname">松鼠旅行官</div><div class="brandnote">替你做攻略的 J 人小松鼠</div></div>
    </div>
    <button class="btn primary" type="button" id="makeTrip">制作我的行程 ↗</button>
  </header>
  <div class="hero">
    <div class="eyebrow">TRAVEL WITH A PLAN · 把行程带在身边</div>
    <h1 id="hTitle"></h1>
    <p id="hSub"></p>
    <div class="stats" id="tripStats"></div>
    <div class="cd">
      <div><span class="cdl" id="cdLabel">距离最近一程出发</span><b id="cdNum">--</b></div>
      <span id="cdWhat"></span>
    </div>
  </div>
  <div class="notice hidden" id="exampleNotice">示例行程 · 展示历史资料整理效果；价格、日期和营业信息请按自己的出行计划重新查询。</div>
  <div class="notice hidden" id="localNotice">本地地图预览版 · 本文件包含你的地图 Key，请勿公开上传。公开分享请重新生成默认版本。</div>
  <p class="trip-note" id="tripNote"></p>
  <div id="panes"></div>
  <footer>
    交通住宿资料日期：__TRIP_Q__ · 地图资料日期：__MAP_Q__。未知信息标为「未查到」，推算标为「估」。<br>
    页面保存的是生成时的资料，票价、库存和营业信息不会自动更新。示意连线仅表示游览顺序。<br>
    <a href="https://github.com/mrliang-github/liangxiao-travel" target="_blank" rel="noopener noreferrer">松鼠旅行官 · 开源 Skill</a> · 良逍制作 · <button type="button" class="pill" id="imaHelp">保存到 ima</button>
  </footer>
</div>

<dialog id="onboarding" aria-labelledby="onboardTitle">
  <div class="dialog-head"><h2 id="onboardTitle">开始你的第一份行程</h2><button type="button" class="close" data-close="onboarding" aria-label="关闭使用引导">×</button></div>
  <div class="dialog-body">
    <p class="trip-note">在电脑上的 WorkBuddy 中制作。首次完成安装和配置后，以后直接说旅行需求。</p>
    <div class="mode-switch"><button class="btn" type="button" id="firstUse" aria-pressed="true">首次使用</button><button class="btn" type="button" id="installedUse" aria-pressed="false">我已安装</button></div>
    <section class="setup-step" id="installStep"><h3>01 · 安装松鼠旅行官</h3>
      <ol><li>下载 <strong>1.2.0 或更新版</strong> Skill 安装包。</li><li>打开 WorkBuddy → 技能 → 添加技能 → 上传技能，选择 ZIP。</li><li>确认「松鼠旅行官」已启用，再复制下面的启动指令。</li></ol>
      <div class="actions"><a class="btn primary" id="downloadSkill" href="@@INSTALL_URL@@" target="_blank" rel="noopener noreferrer">下载安装包</a><a class="btn" href="https://www.codebuddy.cn/work/" target="_blank" rel="noopener noreferrer">获取 WorkBuddy</a></div>
      <p>已经装过旧版「良逍旅行规划」？先备份自己的修改，再导入更新；技术标识仍是 liangxiao-travel。</p>
    </section>
    <section class="setup-step"><h3 id="launchHeading">02 · 在 WorkBuddy 接着完成配置</h3>
      <p>复制到一个新任务发送。助手只引导当前一步，已有配置会跳过；完成后回复「继续」。网页不会读取你的安装状态。</p>
      <label for="launchPrompt" class="t3">启动指令（可直接编辑，旅行需求只需说一次）</label>
      <textarea id="launchPrompt" class="prompt" spellcheck="false"></textarea>
      <div class="actions"><button class="btn primary" type="button" id="copyLaunch">复制启动指令</button><button class="btn" type="button" id="basicLaunch">先做基础攻略</button></div>
      <p class="feedback" id="copyStatus" role="status" aria-live="polite"></p>
    </section>
    <section class="setup-step"><h3>接下来会发生什么？</h3>
      <ol><li><strong>地图：</strong>缺少官方腾讯地图助手时先安装；随后阅读协议并完成手机验证，Key 自动保存，不用自己找。</li><li><strong>同程：</strong>在 WorkBuddy「连应用」完成同程旅行授权，不需要填写 Key。</li><li><strong>规划：</strong>确认出发地、目的地、日期和人数，生成属于你的行程页。</li></ol>
      <p>也可明确选择基础攻略，先整理公开资料和清单；未查询的票价与坐标会留空。申请额度、授权结果以服务方为准。</p>
    </section>
  </div>
</dialog>
<dialog id="imaDialog" aria-labelledby="imaTitle">
  <div class="dialog-head"><h2 id="imaTitle">把行程存入腾讯 ima</h2><button type="button" class="close" data-close="imaDialog" aria-label="关闭 ima 说明">×</button></div>
  <div class="dialog-body"><p>行程文档与当前页面使用同一份资料，适合在手机上查阅和提问。</p>
    <ol><li>下载行程文档，或使用 WorkBuddy 生成的同名 Markdown 文件。</li><li>在 WorkBuddy 中选中文档 → 上传到云端 → ima 知识库；首次使用按官方入口授权。</li><li>确认文档已存入并可检索后，在 ima 选择该知识库，询问某天的安排。</li></ol>
    <div class="actions"><button type="button" class="btn primary" id="downloadDocument">下载行程文档 .md</button></div>
    <p class="feedback" id="documentStatus" role="status"></p>
    <p class="t3">此按钮仅下载文档，不代表已上传 ima。网页待办勾选保存在当前浏览器，不会同步到知识库。资料不会自动刷新。</p>
    <a class="muted-link" href="https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Knowledge-Base/IMA%20Knowledge%20Base/01-Workbuddy-IMA-Basic-Guide" target="_blank" rel="noopener noreferrer">查看官方保存流程 ↗</a>
  </div>
</dialog>

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
var MAP_KEY = @@MAP_KEY@@;
var TRIP_MARKDOWN = @@MARKDOWN@@;
var STORAGE_PREFIX = @@STORAGE_PREFIX@@;

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
  var m=TRIP.meta, num=document.getElementById('cdNum'), what=document.getElementById('cdWhat');
  document.getElementById('cdLabel').textContent=m.isExample?'案例预览':'出行日历';
  if(m.isExample){num.textContent='先看一份，再做你的';what.textContent='点击右上角「制作我的行程」开始。';return;}
  var now=new Date(), start=toDate(m.dateStart), end=toDate(m.dateEnd);
  end.setDate(end.getDate()+1);
  if(!Number.isFinite(start.getTime())||!Number.isFinite(end.getTime())){num.textContent='日期待确认';what.textContent='';return;}
  num.textContent=now<start?'距出发 '+Math.ceil((start-now)/86400000)+' 天':now<end?'行程进行中':'行程已结束';
  what.textContent='按行程日期计算；实际出发时间请核对已确认的车票或机票。';
}

/* 首次使用留在一个 WorkBuddy 任务中；网页不假装能检测本机安装或完成授权。 */
var START_PROMPT='使用「松鼠旅行官」Skill（liangxiao-travel，1.2.0 或更新版）带我完成首次配置和旅行规划。\n先确认版本；若版本不符，提示我安装更新。检查现有配置，每次只引导当前一项，已经完成的跳过。\n将需求与进度保存在当前任务的 outputs/my-trip/onboarding-state.json，不保存 Key、token、手机号或验证码。地图按官方助手流程由我确认协议并完成手机验证；同程由我在连应用授权，完成后我回复“继续”。\n配置完成后，一次询问缺少的出发地、目的地、出行日期和人数；已经提供的不要重复问。生成公开行程页和可存入 ima 的文档。';
function showDialog(id){document.getElementById(id).showModal();}
function bindOnboarding(){
  var prompt=document.getElementById('launchPrompt');
  prompt.value=START_PROMPT;
  document.getElementById('makeTrip').onclick=function(){showDialog('onboarding');};
  document.getElementById('imaHelp').onclick=function(){showDialog('imaDialog');};
  Array.prototype.forEach.call(document.querySelectorAll('[data-close]'),function(b){b.onclick=function(){document.getElementById(b.dataset.close).close();};});
  function mode(installed){
    document.getElementById('installStep').classList.toggle('hidden',installed);
    document.getElementById('firstUse').setAttribute('aria-pressed',String(!installed));
    document.getElementById('installedUse').setAttribute('aria-pressed',String(installed));
    document.getElementById('launchHeading').textContent=installed?'在 WorkBuddy 开始或继续':'02 · 在 WorkBuddy 接着完成配置';
  }
  document.getElementById('firstUse').onclick=function(){mode(false);};
  document.getElementById('installedUse').onclick=function(){mode(true);};
  document.getElementById('basicLaunch').onclick=function(){
    if(prompt.value.indexOf('当前选择：先做基础攻略')===-1) prompt.value+='\n当前选择：先做基础攻略，暂不申请地图 Key、暂不连接同程。仅整理可查的公开资料；未知价格留空，未核实坐标不要写入。';
    document.getElementById('copyStatus').textContent='已加入基础攻略选择，请复制指令到 WorkBuddy。';
  };
  document.getElementById('copyLaunch').onclick=async function(){
    var status=document.getElementById('copyStatus');
    try{await navigator.clipboard.writeText(prompt.value);status.textContent='已复制。切到 WorkBuddy，粘贴到新任务后发送。';}
    catch(e){prompt.focus();prompt.select();status.textContent='浏览器未允许自动复制。文字已选中，请按 Ctrl+C 或 ⌘C 复制。';}
  };
  document.getElementById('downloadDocument').onclick=function(){
    var url=URL.createObjectURL(new Blob([TRIP_MARKDOWN],{type:'text/markdown;charset=utf-8'}));
    var a=document.createElement('a');a.href=url;
    a.download='松鼠旅行官-'+String(TRIP.meta.title||'我的行程').replace(/[\\/:*?"<>|]/g,'-').slice(0,70)+'.md';
    document.body.appendChild(a);a.click();a.remove();setTimeout(function(){URL.revokeObjectURL(url);},1000);
    document.getElementById('documentStatus').textContent='已发起文档下载。接下来在 WorkBuddy 上传至 ima。';
  };
}

/* ===== Tab ===== */
var ICO='fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"';
function ic(d){return '<svg viewBox="0 0 18 18" width="18" height="18" '+ICO+'>'+d+'</svg>';}
var TABS=[
  {k:'traffic',i:ic('<path d="M2.6 11.4h6.2M8.8 11.4 14 6.2M8.8 11.4l5.2 5.2M3.6 5.4h3.6"/>'),l:'交通'},
  {k:'route',i:ic('<path d="M9 15.6s4.6-4.7 4.6-7.7A4.6 4.6 0 0 0 4.4 7.9c0 3 4.6 7.7 4.6 7.7z"/><circle cx="9" cy="7.7" r="1.5"/>'),l:'路线'},
  {k:'plan',i:ic('<rect x="2.6" y="3.8" width="12.8" height="11.6" rx="2.2"/><path d="M2.6 7.3h12.8M6 2.4v2.8M12 2.4v2.8"/>'),l:'行程'},
  {k:'ticket',i:ic('<path d="M2.4 6.4h13.2v1.6a1.6 1.6 0 0 0 0 3.2v1.6H2.4v-1.6a1.6 1.6 0 0 0 0-3.2V6.4z"/><path d="M8.9 5.2v7.6"/>'),l:'门票'},
  {k:'food',i:ic('<path d="M3.2 8.6h11.6a5.8 5.8 0 0 1-11.6 0z"/><path d="M6.4 5.4c0-1.1 1.1-1.1 1.1-2.2M9.9 5.4c0-1.1 1.1-1.1 1.1-2.2"/>'),l:'美食'},
  {k:'todo',i:ic('<rect x="2.6" y="2.6" width="12.8" height="12.8" rx="2.8"/><path d="M5.8 9.2 8.1 11.4 12.4 6.9"/>'),l:'待办'}
];
var active='plan', mapInited=false;
function buildTabs(){
  var bar=document.getElementById('tabbar');
  TABS.forEach(function(t){
    var b=document.createElement('button');
    b.className='tb'+(t.k===active?' on':''); b.dataset.k=t.k;
    b.innerHTML=t.i+t.l;
    b.setAttribute('aria-current',t.k===active?'page':'false');
    b.onclick=function(){switchTab(t.k);};
    bar.appendChild(b);
  });
}
function switchTab(k){
  active=k;
  Array.prototype.forEach.call(document.querySelectorAll('.tb'),function(b){b.classList.toggle('on',b.dataset.k===k);b.setAttribute('aria-current',b.dataset.k===k?'page':'false');});
  Array.prototype.forEach.call(document.querySelectorAll('.pane'),function(p){p.classList.toggle('hidden',p.dataset.k!==k);});
  window.scrollTo({top:0,behavior:'smooth'});
  if(k==='route'){ setTimeout(ensureMap,80); }
}

/* ===== 渲染各 Tab ===== */
function renderTraffic(){
  var people=(TRIP.meta&&TRIP.meta.people)||2;
  var queried=(TRIP.source&&TRIP.source.tripQueryAt)||'';
  var h=['<div class="card"><h2>交通比选'+(queried?' · '+esc(queried):'')+'</h2>'];
  h.push('<div class="sub">单人票价；包含备选班次，不代表已预订。以标注的资料日期和实际查询为准。</div>');
  if(!(TRIP.flightsOrTrains||[]).length) h.push('<p class="t2">尚未查询班次和票价。可在 WorkBuddy 授权同程后补充。</p>');
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
  h.push('</div>');
  return h.join('');
}

function renderRoute(){
  var h=['<div class="card"><h2>把路线看明白</h2>'];
  h.push('<div class="pills" id="viewPills"></div>');
  h.push('<div class="lgd"><span><i style="background:#2f6bff"></i>景点</span><span><i style="background:#e8833a"></i>美食</span><span><i style="background:#c8452c"></i>城市节点</span></div>');
  h.push('<div id="mapbox"><div id="mapCanvas" style="width:100%;height:100%"></div><div class="fb" id="mapFallback"></div></div>');
  h.push('<div class="sub" style="margin:8px 0 0">连线表示游览顺序，不是道路导航或距离计算。没有已核实坐标时，以下方文字顺序为准。</div>');
  h.push('</div>');
  /* 城市小结：按 days 顺序，每天标题拼成该城顺序 */
  h.push('<div class="card"><h2>同城顺序建议</h2>');
  var byCity=Object.create(null), cityOrder=[];
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
  var h=['<div class="section-intro"><div><h2>每天怎么玩</h2><p>展开每天的安排，住宿与注意事项一起看。</p></div><button type="button" class="btn soft" id="planIma">带到 ima ↗</button></div>'];
  (TRIP.days||[]).forEach(function(d,i){
    var y=ymd(d.date);
    h.push('<div class="card day'+(i===0?' open':'')+'" data-day="'+i+'">');
    h.push('<div class="hd" role="button" tabindex="0" aria-expanded="'+(i===0?'true':'false')+'" aria-controls="dayBody'+i+'"><div class="dt"><b>D'+(i+1)+'</b><span>'+y.m+'/'+y.d+'</span></div>'
      +'<div class="tt"><b>'+esc(d.title)+'</b><span>'+esc(d.city)+' · '+weekOf(d.date)+'</span></div>'
      +'<div class="cv">▾</div></div>');
    h.push('<div class="bd" id="dayBody'+i+'">');
    h.push('<div class="slot am"><div class="lb">上午</div><div class="tx">'+esc(d.am)+'</div></div>');
    h.push('<div class="slot pm"><div class="lb">下午</div><div class="tx">'+esc(d.pm)+'</div></div>');
    h.push('<div class="slot ev"><div class="lb">晚上</div><div class="tx">'+esc(d.evening)+'</div></div>');
    (TRIP.hotels||[]).filter(function(hotel){return hotel.date===d.date;}).forEach(function(hotel){
      h.push('<div class="hotel"><div class="hn">住 · '+esc(hotel.name)+'</div><div class="hi">'+esc(hotel.area)+' · '+money(hotel.price)+' '+ptype(hotel.priceType)+'</div><div class="hi">'+esc(hotel.lockAdvice||hotel.alt||'')+'</div></div>');
    });
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
  var g=Object.create(null), order=[];
  (TRIP.days||[]).forEach(function(d){
    (d.foods||[]).forEach(function(f){
      if(!g[d.city]){g[d.city]=[];order.push(d.city);}
      g[d.city].push(f);
    });
  });
  var h=['<div class="card"><h2>吃 · 按城市</h2><div class="sub">资料日期：'+esc(MAP_QUERY)+'。菜名与拍摄建议为参考；价格和营业情况以实际查询为准。</div>'];
  if(!order.length) h.push('<p class="t2">暂无餐厅记录，可在 WorkBuddy 中继续补充。</p>');
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
  var h=['<div class="card"><h2>行前待办</h2><p class="sub">按行程保存在当前浏览器；不会同步到其他设备或 ima。</p>'];
  (TRIP.todos||[]).forEach(function(t,i){
    var id='td_'+i;
    h.push('<label class="ck" data-id="'+id+'"><input type="checkbox" data-ck="'+id+'" data-default="'+(t.done?'1':'0')+'">'
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
    var on=el.dataset.default==='1';
    try{var saved=localStorage.getItem(STORAGE_PREFIX+id);if(saved!==null) on=saved==='1';}catch(e){}
    el.checked=on;
    el.closest('.ck').classList.toggle('done',on);
    el.addEventListener('change',function(){
      el.closest('.ck').classList.toggle('done',el.checked);
      try{ localStorage.setItem(STORAGE_PREFIX+id, el.checked?'1':'0'); }catch(e){}
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
  buildPills();
  if(!MAP_KEY){mapFallback('无需 Key 即可查看示意与文字行程。');return;}
  if(mapInited) return;
  if(typeof TMap!=='undefined' && TMap.Map){ initMap(); return; }
  if(_tmState===2){ return; }
  if(_tmState===1){ _tmWait.push(initMap); return; }
  _tmState=1;
  _tmWait.push(initMap);
  var s=document.createElement('script');
  s.src='https://map.qq.com/api/gljs?v=1&key='+encodeURIComponent(MAP_KEY);
  s.async=true;
  s.onload=function(){
    _tmState=3;
    var a=_tmWait.slice(); _tmWait=[];
    a.forEach(function(f){ try{ f(); }catch(e){ mapFallback('地图暂不可用，请查看文字路线。'); } });
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
      if(typeof p.lat!=='number'||typeof p.lng!=='number'||!Number.isFinite(p.lat)||!Number.isFinite(p.lng)||Math.abs(p.lat)>90||Math.abs(p.lng)>180) return;
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
  if(!map){mapFallback(MAP_KEY?'地图暂不可用，请查看顺序示意。':'无需 Key 即可查看示意与文字行程。');return;}
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
  var points=curView==='all'?CITY_STOPS:pointsFor(curView);
  var illustration='';
  if(points.length){
    var lats=points.map(function(p){return p.lat;}), lngs=points.map(function(p){return p.lng;});
    var minLat=Math.min.apply(null,lats), maxLat=Math.max.apply(null,lats), minLng=Math.min.apply(null,lngs), maxLng=Math.max.apply(null,lngs);
    var positions=points.map(function(p){return {x:maxLng===minLng?220:50+(p.lng-minLng)/(maxLng-minLng)*340,y:maxLat===minLat?100:32+(maxLat-p.lat)/(maxLat-minLat)*130};});
    illustration='<svg viewBox="0 0 440 220" role="img" aria-label="游览顺序示意图"><polyline points="'+positions.map(function(p){return p.x+','+p.y;}).join(' ')+'" stroke="#a8b693" stroke-width="3" stroke-dasharray="6 6" fill="none"/>';
    points.forEach(function(p,i){var xy=positions[i];illustration+='<circle cx="'+xy.x+'" cy="'+xy.y+'" r="13" fill="#355c42"/><text x="'+xy.x+'" y="'+(xy.y+4)+'" text-anchor="middle" fill="white" font-size="11">'+(i+1)+'</text><text x="'+xy.x+'" y="'+(xy.y+30)+'" text-anchor="middle" fill="#24382e" font-size="11">'+esc(String(p.name||'地点').slice(0,12))+'</text>';});
    illustration+='</svg>';
  }else{
    illustration='<div class="route-order">'+(TRIP.meta.destinations||[]).map(function(c,i){return '<span class="route-stop">'+(i+1)+' · '+esc(c)+'</span>';}).join('')+'</div>';
  }
  f.innerHTML='<div style="font-weight:600">'+(points.length?'游览顺序示意':'文字路线 · 坐标尚未核实')+'</div>'+illustration+'<div class="t3">'+esc(msg)+'</div>';
  f.style.display='flex';
}
function initMap(){
  if(mapInited) return;
  var box=document.getElementById('mapbox');
  if(!box || box.offsetWidth===0) return;  // 仍在隐藏 Tab，等下一次
  mapInited=true;
  if(typeof TMap==='undefined' || !TMap.Map){ mapFallback('地图 SDK 不可达（网络或代理未就绪）。'); return; }
  try{
    map=new TMap.Map('mapCanvas',{center:new TMap.LatLng(CITY_VIEWS[0].center[0],CITY_VIEWS[0].center[1]),zoom:CITY_VIEWS[0].zoom});
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
    var info=new TMap.InfoWindow({map:map,position:new TMap.LatLng(CITY_VIEWS[0].center[0],CITY_VIEWS[0].center[1]),offset:{x:0,y:-30},content:''});
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
    setTimeout(function(){applyView(curView);},120);
  }catch(err){
    map=null;
    mapFallback('地图初始化失败，请查看顺序示意与文字路线。');
  }
  setTimeout(function(){
    if(!map) mapFallback('地图长时间未响应（SDK 或代理不可达）。');
  },4000);
}

/* ===== 启动 ===== */
function boot(){
  document.title='松鼠旅行官 · '+TRIP.meta.title;
  document.getElementById('hTitle').textContent=TRIP.meta.title;
  var m=TRIP.meta;
  document.getElementById('hSub').textContent=m.dateStart+' — '+m.dateEnd+' · '+m.days+' 天 · '+m.people+' 人 · '+m.destinations.join(' → ');
  document.getElementById('tripNote').textContent=m.note||'';
  document.getElementById('exampleNotice').classList.toggle('hidden',!m.isExample);
  document.getElementById('localNotice').classList.toggle('hidden',!MAP_KEY);
  document.getElementById('tripStats').innerHTML='<div><b>'+esc(m.days)+'</b><span>天的安排</span></div><div><b>'+esc(m.people)+'</b><span>位旅行搭子</span></div><div><b>'+esc((TRIP.todos||[]).length)+'</b><span>项行前待办</span></div>';
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
    hd.addEventListener('click',function(){hd.parentNode.classList.toggle('open');hd.setAttribute('aria-expanded',String(hd.parentNode.classList.contains('open')));});
    hd.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();hd.click();}});
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
  bindOnboarding();
  document.getElementById('planIma').onclick=function(){showDialog('imaDialog');};
  buildPills();
  mapFallback('无需 Key 即可查看示意与文字行程。');
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
    '@@MAP_KEY@@': script_json(TMAP_KEY),
    '@@MARKDOWN@@': script_json(MARKDOWN),
    '@@STORAGE_PREFIX@@': script_json('squirrel_'+hashlib.sha256(DATA_JS.encode('utf-8')).hexdigest()[:16]+'_'),
    '@@INSTALL_URL@@': escape(args.install_url, quote=True),
}
# 一次替换，避免用户文本里的占位符再次被替换，破坏原数据或带入 Key。
html = re.sub('|'.join(re.escape(k) for k in replacements),
              lambda match: replacements[match.group()], TPL)

if OUT == SRC or not OUT.lower().endswith('.html'):
    parser.error('输出必须是独立的 .html 文件，不能覆盖输入数据')
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, 'w', encoding='utf-8') as stream:
    stream.write(html)
with open(os.path.splitext(OUT)[0]+'.md', 'w', encoding='utf-8') as stream:
    stream.write(MARKDOWN)
print('written', OUT, len(html))
if args.local_map:
    print('本地地图版含访问凭据，不能公开上传。公开版请不加 --local-map 重新生成。', file=sys.stderr)
