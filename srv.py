#!/usr/bin/env python3
"""Monitor server satu file, stdlib only. Run: pm2 start srv.py --name monitor --interpreter python3"""
import concurrent.futures as cf
import hashlib
import hmac
import http.client
import json
import os
import re
import secrets
import shutil
import socket
import ssl
import subprocess
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("PORT", 8899))


def _load_token():
    if os.environ.get("MONITOR_TOKEN"):
        return os.environ["MONITOR_TOKEN"]
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".token")) as f:
            return f.read().strip()
    except Exception:
        return "ganti-saya"


TOKEN = _load_token()
USER = {os.environ.get("MONITOR_USER", "fata"): os.environ.get("MONITOR_PASS", "1232")}
SESSION_TTL = 30 * 24 * 3600  # 30 hari login
PASS = {u: hashlib.sha256(p.encode()).hexdigest() for u, p in USER.items()}


def _load_wa_admin():
    if os.environ.get("MONITOR_WA_ADMIN"):
        return os.environ["MONITOR_WA_ADMIN"].strip()
    try:
        env_path = "/home/fata/.hermes/.env"
        if os.path.isfile(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.startswith("WHATSAPP_ALLOWED_USERS="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        return val.split(",")[0].strip()
    except Exception:
        pass
    return None


_WA_ADMIN = _load_wa_admin()
ALERT_INTERVAL = int(os.environ.get("MONITOR_ALERT_INTERVAL", 300))  # Pengecekan tiap 5 menit
ALERT_COOLDOWN = int(os.environ.get("MONITOR_ALERT_COOLDOWN", 3600))  # Jeda cooldown 1 jam
_alert_cooldown = {}
_prev_pm2_states = {}


def send_wa_alert(message):
    if not _WA_ADMIN:
        return False
    try:
        payload = json.dumps({
            "chatId": f"{_WA_ADMIN}@s.whatsapp.net",
            "message": f"⚠️ *[SERVER MONITOR]*\n{message}"
        }).encode("utf-8")
        req = urllib.request.Request("http://127.0.0.1:3105/send", data=payload,
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=5) as res:
            return res.status == 200
    except Exception:
        return False


def alert_worker():
    global _prev_pm2_states
    time.sleep(30)  # delay saat start
    while True:
        try:
            # 1. Cek status PM2 apps
            out = subprocess.run(["pm2", "jlist"], capture_output=True, text=True, timeout=5).stdout
            current_states = {}
            for p in json.loads(out):
                name = p["name"]
                st = p.get("pm2_env", {}).get("status", "unknown")
                current_states[name] = st
                if _prev_pm2_states:
                    prev_st = _prev_pm2_states.get(name)
                    now_ts = time.time()
                    if prev_st == "online" and st in ("errored", "stopped"):
                        if now_ts - _alert_cooldown.get(f"pm2_{name}", 0) > ALERT_COOLDOWN:
                            send_wa_alert(f"🚨 *PM2 App Error!*\nAplikasi `{name}` berubah status dari *online* menjadi *{st}*.")
                            _alert_cooldown[f"pm2_{name}"] = now_ts
                    elif prev_st in ("errored", "stopped") and st == "online":
                        send_wa_alert(f"✅ *PM2 App Recovered!*\nAplikasi `{name}` sudah kembali *online*.")
                        _alert_cooldown.pop(f"pm2_{name}", None)
            _prev_pm2_states = current_states

            # 2. Cek threshold RAM & Disk
            m = mem()
            if m.get("MemTotal"):
                used_pct = round(100 * (m["MemTotal"] - m.get("MemAvailable", m["MemTotal"])) / m["MemTotal"], 1)
                now_ts = time.time()
                if used_pct >= 90 and now_ts - _alert_cooldown.get("ram_high", 0) > ALERT_COOLDOWN:
                    send_wa_alert(f"🚨 *RAM Kritis!*\nPemakaian RAM mencapai *{used_pct}%*.")
                    _alert_cooldown["ram_high"] = now_ts
            du = shutil.disk_usage("/")
            disk_pct = round(100 * du.used / du.total, 1)
            now_ts = time.time()
            if disk_pct >= 90 and now_ts - _alert_cooldown.get("disk_high", 0) > ALERT_COOLDOWN:
                send_wa_alert(f"🚨 *Disk Storage Kritis!*\nPartisi root `/` mencapai *{disk_pct}%*.")
                _alert_cooldown["disk_high"] = now_ts
        except Exception:
            pass
        time.sleep(ALERT_INTERVAL)


def new_sid(user="fata"):
    exp = int(time.time()) + SESSION_TTL
    data = f"{user}:{exp}"
    sig = hmac.new(TOKEN.encode(), data.encode(), hashlib.sha256).hexdigest()
    return f"{data}:{sig}"


def valid_sid(sid):
    if not sid:
        return False
    parts = sid.split(":")
    if len(parts) != 3:
        return False
    user, exp_str, sig = parts
    try:
        exp = int(exp_str)
    except ValueError:
        return False
    if exp < time.time():
        return False
    if user not in USER:
        return False
    expected_sig = hmac.new(TOKEN.encode(), f"{user}:{exp}".encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, expected_sig)


KNOWN = {22: "ssh", 53: "dns", 80: "nginx", 443: "nginx", 3000: "sapa-server",
         3080: "dsh-web", 3105: "hermes-wa", 5432: "postgres", 6379: "redis",
         8080: "link-shortener", 8899: "monitor", 9119: "hermes-dashboard",
         9090: "adminer", 9091: "cockpit", 20128: "9router"}
HIDE = {20241}  # port internal dinamis, disembunyikan
_prev_cpu = None
_prev_net = None
_BIND = {}
_PORT_NAMES = {}

WEB = [{"port": 8080, "name": "link-shortener", "path": "/", "desc": "s.kemenkopmk.go.id"},
       {"port": 9090, "name": "adminer", "path": "/", "desc": "db admin"},
       {"port": 9091, "name": "cockpit", "path": "/", "desc": "server admin"},
       {"port": 20128, "name": "9router", "path": "/dashboard", "desc": "tunnel dash"},
       {"port": 3080, "name": "dsh-web", "path": "/", "desc": "deepseek harness", "host": "127.0.0.1"},
       {"port": 9119, "name": "hermes-dashboard", "path": "/", "desc": "hermes web ui"},
       {"port": 3000, "name": "sapa-server", "path": "/", "desc": "backend sapa"},
       {"port": 8899, "name": "monitor", "path": "/", "desc": "server monitor"},
       {"name": "sapa-web", "url": "https://sapa.kemenkopmk.go.id", "desc": "portal sapa"}]

PAGE = r"""<!doctype html><html><head><meta charset=utf-8><meta name=viewport
content="width=device-width,initial-scale=1"><title>monitor</title><style>
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:radial-gradient(1200px 400px at 50% -100px,#162033,#0b0e14);color:#e6edf3;font:15px/1.45 system-ui,-apple-system,sans-serif;min-height:100vh}
header{position:sticky;top:0;z-index:5;display:flex;align-items:center;justify-content:space-between;padding:12px 16px;background:rgba(11,14,20,.88);backdrop-filter:blur(10px);border-bottom:1px solid #262d36}
header b{font-size:16px}
.h-right{display:flex;align-items:center;gap:7px;flex-wrap:wrap}
.h-badge{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:3px 8px;font-size:11.5px;color:#79c0ff;font-variant-numeric:tabular-nums;display:inline-flex;align-items:center;gap:4px;white-space:nowrap}
.h-badge.dim{color:#8b949e}
.live{display:flex;align-items:center;gap:7px;font-size:12px;color:#8b949e;font-variant-numeric:tabular-nums}
.live i{width:9px;height:9px;border-radius:50%;background:#3fb950;animation:pl 2s infinite}
@keyframes pl{50%{opacity:.35}}.live.off i{background:#f85149;animation:none}
main{max-width:960px;margin:0 auto;padding:6px 14px 40px}
section,details{margin-top:22px}
summary{list-style:none;cursor:pointer;user-select:none;outline:none}
summary::-webkit-details-marker{display:none}
summary h2{width:100%;margin:0}
summary h2::after{content:'›';font-size:18px;line-height:1;color:#8b949e;margin-left:auto;transition:transform .15s}
details[open] summary h2::after{transform:rotate(90deg)}
details[open] summary h2{margin-bottom:10px}
h2{display:flex;align-items:center;gap:8px;font-size:12px;letter-spacing:.09em;text-transform:uppercase;color:#8b949e;margin:0 0 10px}
.n{background:#21262d;border-radius:99px;padding:1px 9px;font-size:11px;letter-spacing:0}
.grid{display:grid;gap:10px;grid-template-columns:repeat(2,1fr)}
.card.metric{background:linear-gradient(180deg,#171c26,#12161e);border:1px solid #262d36;border-radius:14px;padding:8px 6px 6px;display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:76px}
.card.metric svg{width:100%;max-width:130px;height:auto;display:block}
.card.metric .sv{font-size:17px;font-weight:700;color:#e6edf3;font-variant-numeric:tabular-nums;margin-bottom:3px}
.card.metric .sl{font-size:9.5px;color:#8b949e;letter-spacing:.08em;font-weight:500;text-transform:uppercase}
.wgrid{display:grid;gap:10px;grid-template-columns:1fr}
.card-app{background:linear-gradient(180deg,#171c26,#12161e);border:1px solid #262d36;border-radius:14px;padding:11px 13px;display:flex;flex-direction:column;justify-content:space-between;gap:8px;min-height:72px}
.wtop{display:flex;align-items:center;justify-content:space-between;gap:8px}
.wtit{display:inline-flex;align-items:center;gap:8px;color:inherit;text-decoration:none;min-width:0;flex:1}
.wtit:hover b{color:#58a6ff}
.wtit b{font-size:14.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.wtit .arr{color:#8b949e;font-size:13px;opacity:0.7}
.dot{width:8px;height:8px;flex:none;border-radius:50%;transition:background .3s}
.dot.ok{background:#3fb950;box-shadow:0 0 6px rgba(63,185,80,.5)}
.dot.bad{background:#f85149;box-shadow:0 0 6px rgba(248,81,73,.5)}
.dot.restarting{background:#f0883e;animation:pl .8s infinite}
.wbot{display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap;font-size:11.5px;color:#8b949e}
.wsub{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%}
.wam{display:inline-flex;align-items:center;gap:6px;font-variant-numeric:tabular-nums;color:#8b949e;background:#161b22;border:1px solid #21262d;border-radius:6px;padding:2px 6px;font-size:11px}
.aa{display:flex;align-items:center;gap:4px;flex:none}
.btn{background:#21262d;color:#e6edf3;border:1px solid #30363d;border-radius:6px;padding:2px 7px;font-size:11px;cursor:pointer}
.btn:hover{background:#30363d}.btn:active{background:#2c3440}
.btn.stop{color:#ffa198;border-color:rgba(248,81,73,.3)}.btn.start{color:#7ee787;border-color:rgba(63,185,80,.3)}
.list{background:#11151d;border:1px solid #262d36;border-radius:14px;overflow:hidden}
.row{display:flex;align-items:center;gap:10px;padding:9px 12px;border-bottom:1px solid #1b212b}
.row:last-child{border-bottom:0}
.row code{flex:none;font:12px ui-monospace,SFMono-Regular,monospace;background:#21262d;color:#79c0ff;padding:3px 0;border-radius:8px;min-width:56px;text-align:center}
.row .tx{flex:1;min-width:0}.row .tx b{display:block;font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.row small{color:#8b949e;font-size:12px}
em{flex:none;font-style:normal;font-size:11px;font-weight:700;padding:3px 10px;border-radius:99px}
em.ok{background:rgba(63,185,80,.14);color:#3fb950}em.bad{background:rgba(248,81,73,.14);color:#f85149}
.mv{font-size:12px;color:#8b949e;font-variant-numeric:tabular-nums;flex:none}
.chips{display:flex;flex-wrap:wrap;gap:8px}
.chip{background:#141922;border:1px solid #262d36;padding:6px 12px;border-radius:99px;font-size:12px;color:#8b949e;display:inline-flex;align-items:center;gap:6px}
.chip.ok{border-color:rgba(63,185,80,.3);color:#7ee787}
.chip.bad{border-color:rgba(248,81,73,.3);color:#ffa198}
.modal-bg{position:fixed;inset:0;background:rgba(0,0,0,.75);backdrop-filter:blur(6px);z-index:99;display:none;align-items:center;justify-content:center;padding:16px}
.modal-bg.open{display:flex}
.modal-box{background:#0d1117;border:1px solid #30363d;border-radius:14px;width:100%;max-width:780px;max-height:85vh;display:flex;flex-direction:column;overflow:hidden;box-shadow:0 20px 40px rgba(0,0,0,.8)}
.modal-head{display:flex;align-items:center;justify-content:space-between;padding:10px 16px;background:#161b22;border-bottom:1px solid #30363d}
.modal-head b{font-size:14px;color:#e6edf3}
.modal-body{padding:12px;overflow-y:auto;flex:1;background:#090d13}
.modal-body pre{margin:0;font:11.5px/1.45 ui-monospace,SFMono-Regular,Menlo,monospace;color:#c9d1d9;white-space:pre-wrap;word-break:break-all}
footer{color:#484f58;font-size:12px;text-align:center;margin-top:26px}
.login{max-width:320px;margin:18vh auto 0;padding:26px 22px;text-align:center}
.login h1{font-size:20px;margin:0 0 4px}.login p{color:#8b949e;font-size:13px;margin:0 0 16px}
.login input{width:100%;background:#0d1117;border:1px solid #30363d;color:#e6edf3;border-radius:10px;padding:12px;margin-bottom:10px;font-size:15px}
.login button{width:100%;background:#238636;border:0;color:#fff;border-radius:10px;padding:12px;font-size:15px;min-height:48px;cursor:pointer}
.login .err{color:#f85149;font-size:13px;min-height:20px;margin-bottom:6px}
.lout{background:none;border:1px solid #30363d;color:#8b949e;border-radius:8px;padding:4px 10px;font-size:12px;cursor:pointer}
@media(min-width:600px){.grid{grid-template-columns:repeat(4,1fr)}.wgrid{grid-template-columns:repeat(2,1fr)}}
@media(min-width:900px){main{padding:6px 20px 40px}.grid{grid-template-columns:repeat(4,1fr)}.wgrid{grid-template-columns:repeat(3,1fr)}}
</style></head><body><header><b>⚙️ server</b>
<div class=h-right>
<span class=h-badge id=net>↓ 0 KB/s · ↑ 0 KB/s</span>
<span class="h-badge dim" id=upt>up …</span>
<span class="h-badge dim" id=swp>sw 0/4G</span>
<span class=live id=live><i></i><span id=ts>…</span></span>
<button class=lout onclick="logout()">keluar</button></div></header><main>
<section><div class=grid id=sys></div></section>
<section><h2>apps <span class=n id=an></span></h2><div class=wgrid id=apps></div></section>
<details open><summary><h2>processes <span class=n id=rn></span></h2></summary><div class=list id=proc style="margin-top:10px"></div></details>
<details><summary><h2>docker <span class=n id=dn></span></h2></summary><div class=chips id=doc style="margin-top:10px"></div></details>
<details><summary><h2>systemd <span class=n id=sdn></span></h2></summary><div class=chips id=sd style="margin-top:10px"></div></details>
<details><summary><h2>ports & services <span class=n id=sn></span></h2></summary><div class=list id=svc style="margin-top:10px"></div></details>
<details><summary><h2>nginx vhosts <span class=n id=nn></span></h2></summary><div class=chips id=ngx style="margin-top:10px"></div></details>
<footer>auto-refresh 3s · <span id=h></span></footer></main>
<div class=modal-bg id=m-bg onclick="if(event.target===this)closeLog()">
<div class=modal-box><div class=modal-head><b id=m-title>📋 Logs</b><div style="display:flex;align-items:center;gap:6px"><button class=btn onclick="refreshLog()">↻ refresh</button><button class=btn onclick="copyLog()">📋 copy</button><button class=btn onclick="closeLog()">✕ tutup</button></div></div><div class=modal-body><pre id=m-logs>Memuat log...</pre></div></div>
</div>
<script>
const g=id=>document.getElementById(id);
let curLogApp=null;
let _restarting={};
function clr(pct){
if(pct>=90)return'#f85149';
if(pct>=75)return'#f0883e';
if(pct>=55)return'#e3b341';
if(pct>=30)return'#38d39f';
return'#3fb950';
}
function metric(l,v,p,unit){
const valStr=`${v}${unit||''}`;
if(p==null){
return `<div class="card metric"><span class=sv>${valStr}</span><span class=sl>${l.toUpperCase()}</span></div>`;
}
const pct=Math.min(100,Math.max(0,p));
const off=(119.4*(1-pct/100)).toFixed(1);
const c=clr(pct);
const fz=valStr.length>7?'10.5px':valStr.length>5?'12.5px':'14.5px';
const arc=`<path d="M 12 50 A 38 38 0 0 1 88 50" fill="none" stroke="${c}" stroke-width="6.5" stroke-linecap="round" stroke-dasharray="119.4" stroke-dashoffset="${off}" style="transition:stroke-dashoffset .5s ease,stroke .5s"/>`;
return `<div class="card metric"><svg viewBox="0 0 100 58"><path d="M 12 50 A 38 38 0 0 1 88 50" fill="none" stroke="#212733" stroke-width="6.5" stroke-linecap="round"/>${arc}<text x="50" y="37" text-anchor="middle" fill="#e6edf3" font-size="${fz}" font-weight="700" font-family="system-ui,-apple-system,sans-serif">${valStr}</text><text x="50" y="52" text-anchor="middle" fill="#8b949e" font-size="9px" letter-spacing="0.08em" font-family="system-ui,-apple-system,sans-serif">${l.toUpperCase()}</text></svg></div>`}
async function tick(){try{const d=await(await fetch('/api')).json();
g('ts').textContent=d.time;g('live').classList.remove('off');g('h').textContent=location.hostname;
if(d.net_rx&&d.net_tx)g('net').textContent=`↓ ${d.net_rx} · ↑ ${d.net_tx}`;
const uptimeStr=d.uptime.replace(/^0d\s*/,'').replace(/^0h\s*/,'')||d.uptime;
const swapStr=d.swap_total_gb?`${d.swap_used_gb}/${d.swap_total_gb}G`:`${d.swap_used_gb||0}G`;
if(g('upt'))g('upt').textContent=`up ${uptimeStr}`;
if(g('swp'))g('swp').textContent=`sw ${swapStr}`;
const loadVal=parseFloat(d.load.split(' ')[0])||0;
const loadPct=Math.min(100,Math.round((loadVal/(d.cores||4))*100));
g('sys').innerHTML=metric('cpu',d.cpu,d.cpu,'%')+metric('mem',d.mem_pct,d.mem_pct,'%')
+metric('disk',d.disk_pct,d.disk_pct,'%')+metric('load',d.load.split(' ')[0],loadPct);
g('sn').textContent=d.services.length;g('rn').textContent=d.top.length;
g('svc').innerHTML=d.services.map(s=>`<div class=row><code>:${s.port}</code><div class=tx><b>${s.name}</b><small>${s.via} · ${s.detail}</small></div><em class=${s.ok?'ok':'bad'}>${s.ok?'●':'○'}</em></div>`).join('');
const h=location.hostname;
const pm2Map=Object.fromEntries((d.pm2||[]).map(p=>[p.name,p]));
const knownWeb=new Set();
const items=(d.web||[]).map(w=>{
knownWeb.add(w.name);
const p=pm2Map[w.name]||null;
const svc=w.port?(d.services||[]).find(s=>s.port==w.port):null;
let ok=false;
if(w.url){
ok=!!d.sites?.[w.name];
}else if(p&&svc){
ok=(p.status==='online')&&!!svc.ok;
}else if(p){
ok=(p.status==='online');
}else if(svc){
ok=!!svc.ok;
}
if(_restarting[w.name])ok=false;
const host=w.host||h;
const link=w.url||(w.port?`http://${host}:${w.port}${w.path||'/'}`:null);
const sub=w.url?w.url.replace('https://',''):(w.port?`${host}:${w.port} · ${w.desc}`:(w.desc||''));
return{name:w.name,link,sub,ok,pm2:p,restarting:!!_restarting[w.name]};
});
(d.pm2||[]).forEach(p=>{
if(!knownWeb.has(p.name)){
let ok=(p.status==='online');
if(_restarting[p.name])ok=false;
items.push({name:p.name,link:null,sub:`pm2 service · ${p.status}`,ok,pm2:p,restarting:!!_restarting[p.name]});
}
});
g('an').textContent=items.length;
g('apps').innerHTML=items.map(it=>{
const dotClass=it.restarting?'dot restarting':(it.ok?'dot ok':'dot bad');
const tit=it.link?`<a class=wtit target=_blank rel="noreferrer noopener" href="${it.link}"><span class="${dotClass}"></span><b>${it.name}</b><span class=arr>↗</span></a>`:`<div class=wtit><span class="${dotClass}"></span><b>${it.name}</b></div>`;
const acts=it.pm2?`<div class=aa><button class=btn title="Lihat Log" onclick="showLog('${it.pm2.name}')">📄 log</button><button class=btn title="Restart ${it.pm2.name}" onclick="act('${it.pm2.name}','restart')">↻</button>${it.pm2.status=='online'?`<button class="btn stop" title="Stop ${it.pm2.name}" onclick="act('${it.pm2.name}','stop')">■</button>`:`<button class="btn start" title="Start ${it.pm2.name}" onclick="act('${it.pm2.name}','start')">▶</button>`}</div>`:'';
const stateLabel=it.restarting?'restarting...':(it.pm2?(!it.ok?(it.pm2.status==='online'?'starting...':it.pm2.status):'up '+it.pm2.uptime):'');
const meta=it.pm2?`<span class=wam><span>${it.pm2.cpu}</span><span>${it.pm2.mem}</span><span>${stateLabel}</span></span>`:'';
return `<div class=card-app><div class=wtop>${tit}${acts}</div><div class=wbot><span class=wsub>${it.sub}</span>${meta}</div></div>`;
}).join('');
g('ngx').innerHTML=d.nginx.map(n=>`<span class=chip>${n}</span>`).join('')||'<span class=chip>n/a</span>';g('nn').textContent=d.nginx.length;
g('proc').innerHTML=d.top.map(p=>`<div class=row><code>${p.pid}</code><div class=tx><b>${p.name}</b></div><span class=mv>${p.mem}</span></div>`).join('');
g('doc').innerHTML=(d.docker||[]).map(c=>`<span class="chip ${c.ok?'ok':'bad'}"><span class="dot ${c.ok?'ok':'bad'}"></span><b>${c.name}</b> <small>(${c.status})</small></span>`).join('')||'<span class=chip>tidak ada container aktif</span>';
g('dn').textContent=(d.docker||[]).length;
g('sd').innerHTML=(d.systemd||[]).map(s=>`<span class="chip ${s.ok?'ok':'bad'}"><span class="dot ${s.ok?'ok':'bad'}"></span>${s.name} <small>(${s.status})</small></span>`).join('')||'<span class=chip>n/a</span>';
g('sdn').textContent=(d.systemd||[]).length;
}catch(e){console.error('tick error:',e);g('ts').textContent='offline';g('live').classList.add('off')}}setInterval(tick,3000);tick()
async function act(name,op){if(op!='start'&&!confirm(`${op} ${name}?`))return;
_restarting[name]=true;tick();
try{
const r=await fetch('/act',{method:'POST',body:JSON.stringify({name,op})});
if(r.status==401){location.href='/login';return}
if(!r.ok)alert('gagal: '+await r.text());
}catch(e){alert('error: '+e)}
finally{delete _restarting[name]}
tick();
let n=0;
const fastPoll=setInterval(()=>{n++;tick();if(n>=20)clearInterval(fastPoll)},1000);}
async function showLog(name){
curLogApp=name;
g('m-title').textContent=`📋 Logs: ${name}`;
g('m-logs').textContent='Mengambil log...';
g('m-bg').classList.add('open');
refreshLog();
}
async function refreshLog(){
if(!curLogApp)return;
try{
const r=await fetch(`/logs?name=${encodeURIComponent(curLogApp)}&lines=60`);
if(r.status==401){location.href='/login';return}
const d=await r.json();
g('m-logs').textContent=d.logs||'(log kosong)';
}catch(e){g('m-logs').textContent='Gagal memuat log: '+e}}
function copyLog(){navigator.clipboard.writeText(g('m-logs').textContent);alert('Log berhasil disalin ke clipboard!')}
function closeLog(){g('m-bg').classList.remove('open');curLogApp=null}
window.addEventListener('keydown',e=>{if(e.key==='Escape')closeLog()});
async function logout(){await fetch('/logout',{method:'POST'});location.href='/login'}</script></body></html>"""

LOGIN = """<!doctype html><html><head><meta charset=utf-8><meta name=viewport
content="width=device-width,initial-scale=1"><title>login · monitor</title><style>
*{box-sizing:border-box}body{margin:0;background:radial-gradient(1200px 400px at 50% -100px,#162033,#0b0e14);color:#e6edf3;font:15px system-ui;min-height:100vh}
.login{max-width:320px;margin:18vh auto 0;padding:26px 22px;text-align:center;background:linear-gradient(180deg,#171c26,#12161e);border:1px solid #262d36;border-radius:16px}
.login h1{font-size:20px;margin:0 0 4px}.login p{color:#8b949e;font-size:13px;margin:0 0 16px}
.login input{width:100%;background:#0d1117;border:1px solid #30363d;color:#e6edf3;border-radius:10px;padding:12px;margin-bottom:10px;font-size:15px}
.login button{width:100%;background:#238636;border:0;color:#fff;border-radius:10px;padding:12px;font-size:15px;min-height:48px;cursor:pointer}
.login .err{color:#f85149;font-size:13px;min-height:20px;margin-bottom:6px}
</style></head><body><form class=login method=post action=/login>
<h1>⚙️ monitor</h1><p>masuk untuk kelola server</p>
<div class=err>ERR</div>
<input name=user placeholder=user autocomplete=username autofocus>
<input name=pass type=password placeholder=password autocomplete=current-password>
<button>masuk</button></form></body></html>"""


def cpu_pct():
    global _prev_cpu
    with open("/proc/stat") as f:
        n = list(map(int, f.readline().split()[1:]))
    idle, total = n[3] + n[4], sum(n)
    if _prev_cpu:
        (pi, pt) = _prev_cpu
        pct = round(100 * (1 - (idle - pi) / (total - pt)), 1) if total > pt else 0.0
    else:
        pct = 0.0
    _prev_cpu = (idle, total)
    return pct


def mem():
    d = {}
    with open("/proc/meminfo") as f:
        for line in f:
            k, v = line.split(":")
            if k in ("MemTotal", "MemAvailable", "SwapTotal", "SwapFree"):
                d[k.strip()] = int(v.split()[0])
    return d


def net_speed():
    global _prev_net
    now = time.time()
    rx_total = 0
    tx_total = 0
    try:
        with open("/proc/net/dev") as f:
            for l in f.readlines()[2:]:
                parts = l.split(":")
                if len(parts) == 2 and parts[0].strip() != "lo":
                    cols = parts[1].split()
                    rx_total += int(cols[0])
                    tx_total += int(cols[8])
    except Exception:
        return "0 KB/s", "0 KB/s"

    if _prev_net:
        prx, ptx, pt = _prev_net
        dt = max(0.5, now - pt)
        rx_s = (rx_total - prx) / dt
        tx_s = (tx_total - ptx) / dt

        def fmt(bps):
            if bps >= 1048576:
                return f"{bps / 1048576:.1f} MB/s"
            return f"{bps / 1024:.0f} KB/s"
        res = (fmt(rx_s), fmt(tx_s))
    else:
        res = ("0 KB/s", "0 KB/s")
    _prev_net = (rx_total, tx_total, now)
    return res


def listeners(pm2_map=None):
    try:
        out = subprocess.run(["ss", "-tlnpH"], capture_output=True, text=True, timeout=5).stdout
        ports = set()
        _BIND.clear()
        _PORT_NAMES.clear()
        for line in out.splitlines():
            parts = line.split()
            if len(parts) < 4:
                continue
            addr = parts[3]
            ip, port_str = addr.rsplit(":", 1)
            try:
                port = int(port_str)
            except ValueError:
                continue
            ports.add(port)
            h = ip.strip("[]")
            if h in ("0.0.0.0", "*", "::"):
                h = "127.0.0.1"
            _BIND.setdefault(port, h)
            if h == "127.0.0.1":
                _BIND[port] = h
            m_pid = re.search(r'pid=(\d+)', line)
            m_proc = re.search(r'users:\(\("([^"]+)"', line)
            p_name = None
            if m_pid and pm2_map and m_pid.group(1) in pm2_map:
                p_name = pm2_map[m_pid.group(1)]
            elif m_proc:
                p_name = m_proc.group(1).split()[0].replace('"', '')
            if p_name and port not in _PORT_NAMES:
                _PORT_NAMES[port] = p_name
        return sorted(p for p in ports if p in KNOWN or (p < 32768 and p not in HIDE))
    except Exception:
        return sorted(KNOWN)


def target(port):
    return _BIND.get(port, "127.0.0.1")


def check_http(port, https=False):
    host = target(port)
    try:
        if https:
            c = http.client.HTTPSConnection(host, port, timeout=2,
                                            context=ssl._create_unverified_context())
        else:
            c = http.client.HTTPConnection(host, port, timeout=2)
        c.request("GET", "/")
        s = c.getresponse().status
        return True, f"http {s}"
    except Exception as e:
        return False, type(e).__name__


def check_tcp(port):
    host = target(port).split("%")[0]
    try:
        socket.create_connection((host, port), timeout=2).close()
        return True, "open"
    except Exception as e:
        return False, type(e).__name__


def check_one(port):
    name = KNOWN.get(port) or _PORT_NAMES.get(port) or f"port-{port}"
    if port == 443:
        ok, d = check_http(port, https=True)
        return {"port": port, "name": name, "via": "https", "ok": ok, "detail": d}
    ok_http, d_http = check_http(port)
    if ok_http:
        return {"port": port, "name": name, "via": "http", "ok": True, "detail": d_http}
    ok_tcp, d_tcp = check_tcp(port)
    return {"port": port, "name": name, "via": "tcp", "ok": ok_tcp, "detail": d_tcp}


def pm2():
    try:
        out = subprocess.run(["pm2", "jlist"], capture_output=True, text=True, timeout=5).stdout
        rows = []
        mapping = {}
        for p in json.loads(out):
            e = p.get("pm2_env", {})
            up = e.get("pm_uptime", 0)
            ups = f"{int((time.time()*1000-up)/3600000)}h" if up else "-"
            mon = p.get("monit", {})
            pid = p.get("pid")
            if pid:
                mapping[str(pid)] = p["name"]
            rows.append({"name": p["name"], "status": e.get("status", "?"),
                          "cpu": f"{p.get('monit', {}).get('cpu', '?')}%",
                          "mem": f"{round(mon.get('memory', 0)/1048576)}MB" if mon.get("memory") else "-",
                          "uptime": ups})
        return rows, mapping
    except Exception:
        return [], {}


def nginx():
    try:
        vhosts = []
        d = "/etc/nginx/sites-enabled"
        for fn in sorted(os.listdir(d)):
            with open(os.path.join(d, fn)) as f:
                names = [w.strip(";") for line in f for w in
                         (line.strip().split()[1:] if line.strip().startswith("server_name") else [])]
            vhosts.append(f"{fn} ({', '.join(names) or '?'})")
        return vhosts
    except Exception:
        return []


def docker_containers():
    try:
        r = subprocess.run(["docker", "ps", "-a", "--format", "{{.Names}}\t{{.Status}}\t{{.Image}}\t{{.Ports}}"],
                           capture_output=True, text=True, timeout=3)
        res = []
        for l in r.stdout.strip().splitlines():
            if not l.strip():
                continue
            parts = l.split("\t")
            name = parts[0]
            st = parts[1] if len(parts) > 1 else ""
            img = parts[2] if len(parts) > 2 else ""
            res.append({"name": name, "status": st, "image": img, "ok": "Up" in st})
        return res
    except Exception:
        return []


def systemd_services():
    units = ["tailscaled", "nginx", "docker", "ssh", "postgresql", "redis-server", "hermes-gateway"]
    res = []
    for u in units:
        try:
            r = subprocess.run(["systemctl", "is-active", u], capture_output=True, text=True, timeout=2)
            st = r.stdout.strip()
            if st != "active":
                r_u = subprocess.run(["systemctl", "--user", "is-active", u], capture_output=True, text=True, timeout=2)
                st_u = r_u.stdout.strip()
                if st_u == "active":
                    st = st_u
            st = st or "inactive"
            res.append({"name": u, "status": st, "ok": st == "active"})
        except Exception:
            pass
    return res


def _clean_name(pid, raw_name, pm2_map):
    if pm2_map and pid in pm2_map:
        return pm2_map[pid]
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            cmd = f.read().replace(b"\x00", b" ").decode(errors="ignore").strip()
    except Exception:
        cmd = ""
    if "whatsapp-bridge" in cmd:
        return "whatsapp-bridge"
    if "hermes_cli" in cmd or "hermes-agent" in cmd:
        return "hermes"
    if "9router" in cmd:
        return "9router"
    if "dsh" in cmd:
        return "dsh"
    if "agy" in cmd:
        return "agy"
    return raw_name


def top(pm2_map=None):
    rows = []
    for pid in filter(str.isdigit, os.listdir("/proc")):
        try:
            with open(f"/proc/{pid}/status") as f:
                st = dict(l.split(":", 1) for l in f if ":" in l)
            rss = int(st.get("VmRSS", "0 kB").split()[0])
            if rss:
                name = _clean_name(pid, st["Name"].strip(), pm2_map)
                rows.append({"pid": pid, "name": name, "kb": rss})
        except Exception:
            pass
    rows.sort(key=lambda r: -r["kb"])
    return [{"pid": r["pid"], "name": r["name"],
             "mem": f"{r['kb']//1024}MB" if r["kb"] >= 1024 else f"{r['kb']}KB"} for r in rows[:8]]


def site_ok(url):
    host = url.split("/")[2]
    try:
        ctx = ssl._create_unverified_context()
        c = http.client.HTTPSConnection(host, timeout=2, context=ctx)
        c.request("GET", "/")
        if 200 <= c.getresponse().status < 500:
            return True
    except Exception:
        pass
    try:
        ctx = ssl._create_unverified_context()
        c = http.client.HTTPSConnection("127.0.0.1", 443, timeout=2, context=ctx)
        c.request("GET", "/", headers={"Host": host})
        return 200 <= c.getresponse().status < 500
    except Exception:
        return False


def dsh_token():
    try:
        log_path = os.path.expanduser("~/.pm2/logs/dsh-web-out.log")
        if os.path.isfile(log_path):
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in reversed(f.readlines()):
                    m = re.search(r"token=([a-zA-Z0-9_-]+)", line)
                    if m:
                        return m.group(1)
        out = subprocess.run(["pm2", "logs", "dsh-web", "--nostream", "--lines", "25"],
                             capture_output=True, text=True, timeout=2).stdout
        m = re.findall(r"token=([a-zA-Z0-9_-]+)", out)
        if m:
            return m[-1]
    except Exception:
        pass
    return None


def snapshot():
    m = mem()
    used = m.get("MemTotal", 0) - m.get("MemAvailable", 0)
    sw_tot = m.get("SwapTotal", 0)
    sw_free = m.get("SwapFree", 0)
    sw_used = sw_tot - sw_free
    sw_used_gb = round(sw_used / 1048576, 1) if sw_tot else 0
    rx_s, tx_s = net_speed()
    du = shutil.disk_usage("/")
    with open("/proc/loadavg") as f:
        load = " ".join(f.read().split()[:3])
    with open("/proc/uptime") as f:
        s = int(float(f.read().split()[0]))
    pm2_rows, pm2_map = pm2()
    ports = listeners(pm2_map)
    with cf.ThreadPoolExecutor(max_workers=16) as ex:
        svcs = list(ex.map(check_one, ports))
        sites = {w["name"]: ex.submit(site_ok, w["url"]).result()
                 for w in WEB if w.get("url")}
    tok = dsh_token()
    web_list = []
    for w in WEB:
        item = dict(w)
        if item.get("name") == "dsh-web" and tok:
            item["path"] = f"/?token={tok}"
        web_list.append(item)
    return {"time": time.strftime("%H:%M:%S"),
            "cpu": cpu_pct(), "mem_pct": round(100 * used / m["MemTotal"], 1) if m.get("MemTotal") else 0,
            "disk_pct": round(100 * du.used / du.total, 1), "load": load, "cores": os.cpu_count() or 1,
            "uptime": f"{s//86400}d {s%86400//3600}h {s%3600//60}m",
            "swap_used_gb": sw_used_gb,
            "swap_total_gb": round(sw_tot / 1048576, 1) if sw_tot else 0,
            "net_rx": rx_s, "net_tx": tx_s,
            "nproc": len([p for p in os.listdir('/proc') if p.isdigit()]),
            "services": svcs, "web": web_list, "sites": sites,
            "pm2": pm2_rows, "nginx": nginx(), "top": top(pm2_map),
            "docker": docker_containers(), "systemd": systemd_services()}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _sid(self):
        for part in (self.headers.get("Cookie") or "").split(";"):
            k, _, v = part.strip().partition("=")
            if k.strip() == "sid" and valid_sid(v.strip()):
                return v.strip()
        return None

    def _send(self, code, body=b"", ctype="text/plain", cookie=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_POST(self):
        if self.path == "/login":
            n = int(self.headers.get("Content-Length", 0))
            f = urllib.parse.parse_qs(self.rfile.read(n).decode())
            u, p = f.get("user", [""])[0], f.get("pass", [""])[0]
            if PASS.get(u) and hmac.compare_digest(
                    PASS[u], hashlib.sha256(p.encode()).hexdigest()):
                sid = new_sid(u)
                self.send_response(303)
                self.send_header("Location", "/")
                self.send_header("Set-Cookie", f"sid={sid}; Path=/; Max-Age={SESSION_TTL}; HttpOnly; SameSite=Lax")
                self.end_headers()
            else:
                self._send(200, LOGIN.replace("ERR", "user/pass salah").encode(), "text/html")
            return
        if self.path == "/logout":
            self._send(200, b"ok", cookie="sid=; Path=/; Max-Age=0")
            return
        if self.path != "/act":
            return self._send(404)
        if not self._sid():
            return self._send(401, b"login dulu")
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        except Exception:
            return self._send(400, b"bad json")
        name, op = body.get("name", ""), body.get("op", "")
        if op not in ("restart", "stop", "start") or not name:
            return self._send(400, b"bad op/name")
        try:
            names = [p["name"] for p in json.loads(subprocess.run(
                ["pm2", "jlist"], capture_output=True, text=True, timeout=5).stdout)]
        except Exception:
            return self._send(500, b"pm2 error")
        if name not in names:
            return self._send(400, b"unknown app")
        r = subprocess.run(["pm2", op, name], capture_output=True, text=True, timeout=30)
        return self._send(200 if r.returncode == 0 else 500, (r.stderr or r.stdout or "ok").encode())

    def do_GET(self):
        if self.path == "/login":
            return self._send(200, LOGIN.replace("ERR", "").encode(), "text/html")
        if not self._sid():
            self.send_response(303)
            self.send_header("Location", "/login")
            self.end_headers()
            return
        if self.path == "/":
            body, ctype = PAGE.encode(), "text/html"
        elif self.path == "/api":
            try:
                body, ctype = json.dumps(snapshot()).encode(), "application/json"
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                return
        elif self.path.startswith("/logs?"):
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            name = qs.get("name", [""])[0]
            lines = int(qs.get("lines", [50])[0])
            lines = min(max(10, lines), 200)
            try:
                names = [p["name"] for p in json.loads(subprocess.run(
                    ["pm2", "jlist"], capture_output=True, text=True, timeout=5).stdout)]
            except Exception:
                names = []
            if name not in names:
                return self._send(400, b"unknown app")
            try:
                out = subprocess.run(["pm2", "logs", name, "--lines", str(lines), "--nostream"],
                                     capture_output=True, text=True, timeout=8)
                log_text = out.stdout or out.stderr or "(tidak ada log)"
                body, ctype = json.dumps({"name": name, "logs": log_text}).encode(), "application/json"
            except Exception as e:
                body, ctype = json.dumps({"name": name, "logs": f"Error: {e}"}).encode(), "application/json"
        else:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    # Start background WhatsApp watcher
    threading.Thread(target=alert_worker, daemon=True).start()
    ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
