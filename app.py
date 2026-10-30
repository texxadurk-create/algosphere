flask
websockets
python-telegram-bot
# ALGOSPHERE by TEXXADURK - Complete
import os, sys, time, json, base64, asyncio, threading
from datetime import datetime, timezone
from collections import Counter, deque
try:
    import websockets
except ImportError:
    print("Missing package: pip install websockets flask python-telegram-bot")
    sys.exit(1)
from flask import Flask, request, jsonify, Response
DERIV_WS_URL = os.getenv("DERIV_WS_URL", "wss://ws.derivws.com/websockets/v3?app_id=1089")
PORT = int(os.getenv("PORT", "3000"))
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "9271580025:AAE0lGxG5qbBIvcm-wyz8UOgdOT_Wi-0nWo")
app = Flask(__name__)
STATE = {"status": "WAITING FOR SETUP","balance": 0.0, "currency": "USD", "loginid": "", "is_demo": True, "profit_today": 0.0, "trades_today": 0,"wins": 0, "losses": 0, "session": 1, "max_sessions": 3,"trades_in_session": 0,"last_scan": {"even_pct": 0, "over2_pct": 0, "rare_digit": "-", "rare_freq": 0},"logs": deque(maxlen=150), "paused": False, "running": False,}
BOT_CONFIG = {"api_token": "","account_type": "DEMO", "market": "R_100", "stake_mode": "Auto %","auto_pct": 1.5, "fixed_stake": 1.0, "take_profit": 3.0, "stop_loss": 4.0,"trades_per_session": 5, "min_confidence": 62,}
bot_thread = None
control_flags = {"stop": False, "pause": False}
ticks_buffer = deque(maxlen=100)
LOGO_SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="60" height="60" viewBox="0 0 60 60"><circle cx="30" cy="30" r="28" fill="#0A0A0A" stroke="#FF0033" stroke-width="1.5"/><circle cx="30" cy="30" r="14" fill="black" stroke="#FF0033" stroke-width="1"/><text x="30" y="35" text-anchor="middle" font-family="Orbitron" font-weight="900" font-size="16" fill="#FF0033">A</text></svg>'
def log_msg(msg):
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    line = f"[{ts} GMT] {msg}"
    STATE["logs"].append(line)
    print(line, flush=True)
def set_status(s):
    STATE["status"] = s
    log_msg(f"STATUS: {s}")
@app.route("/logo.svg")
def logo():
    return Response(LOGO_SVG, mimetype="image/svg+xml")
@app.route("/")
def store():
    return '''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ALGOSPHERE</title><link rel="icon" href="/logo.svg"><link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&display=swap" rel="stylesheet"><style>body{background:#0A0A0A;color:white;font-family:monospace;margin:0}h1{font-family:Orbitron}.hero{text-align:center;padding:60px 20px}.btn{background:#FF0033;color:black;font-family:Orbitron;font-weight:900;padding:18px 36px;border:none;clip-path:polygon(10% 0,100% 0,90% 100%,0 100%);cursor:pointer;font-size:18px}.btn:hover{box-shadow:0 0 25px #FF0033}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;max-width:900px;margin:30px auto;padding:0 20px}.card{border:1px solid #222;padding:20px;background:#111}.accent{color:#FF0033}.warn{color:#888;font-size:12px;text-align:center;margin:40px}</style></head><body><div class="hero"><img src="/logo.svg" width="80"><h1 style="font-size:42px">ALGOSPHERE</h1><div class="accent" style="font-family:Orbitron">by TEXXADURK</div><p>Disciplined digit-trading bot for Deriv. Capital protection first.</p><a href="/dashboard"><button class="btn">OPEN BOT</button></a></div><div class="cards"><div class="card"><b class="accent">Safe risk limits</b><br><small>Auto 1.5% max 2%, daily +$3 / -$4 stop.</small></div><div class="card"><b class="accent">No recovery</b><br><small>Never martingale.</small></div><div class="card"><b class="accent">Live dashboard</b><br><small>100-tick scan, confidence scoring.</small></div><div class="card"><b class="accent">Demo-first</b><br><small>Test on DEMO before REAL.</small></div></div><div class="warn">Risk: Trading involves risk. Digit results are random. Goal is capital protection, not guaranteed wins. Test on DEMO first.</div></body></html>'''
@app.route("/dashboard")
def dashboard():
    return '''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ALGOSPHERE Dashboard</title><link rel="icon" href="/logo.svg"><link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&display=swap" rel="stylesheet"><style>:root{--bg:#0A0A0A;--red:#FF0033;--yellow:#FFE600;--grey:#1A1A1A}body{background:var(--bg);color:white;font-family:monospace;margin:0}.top{display:flex;justify-content:space-between;align-items:center;padding:12px 16px;border-bottom:1px solid #222;background:#0F0F0F}h1{font-family:Orbitron;margin:0;font-size:22px}small.red{color:var(--red);font-family:Orbitron;font-size:10px}.badge{padding:4px 10px;border:1px solid #333;font-size:12px}.badge.demo{color:var(--yellow);border-color:var(--yellow)}.badge.real{color:var(--red);border-color:var(--red)}.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;padding:12px}@media(max-width:700px){.grid{grid-template-columns:1fr}}.panel{background:var(--grey);border:1px solid #222;padding:14px}.panel h3{font-family:Orbitron;font-size:12px;margin:0 0 10px;color:var(--red)}input,select{width:100%;background:black;color:white;border:1px solid #333;padding:8px;margin:4px 0;font-family:monospace}.btn{font-family:Orbitron;font-weight:900;padding:12px 20px;border:none;cursor:pointer;clip-path:polygon(8% 0,100% 0,92% 100%,0 100%);margin:4px}.btn-red{background:var(--red);color:black}.btn-yellow{background:var(--yellow);color:black}.btn-grey{background:#333;color:white}.log{height:280px;overflow-y:auto;background:black;color:var(--red);font-size:11px;padding:8px;border:1px solid #222;white-space:pre-wrap}.stat{display:flex;justify-content:space-between;font-size:12px;padding:4px 0;border-bottom:1px dashed #222}</style></head><body><div class="top"><div style="display:flex;align-items:center;gap:10px"><img src="/logo.svg" width="44"><div><h1>ALGOSPHERE</h1><small class="red">by TEXXADURK</small></div></div><div style="text-align:right"><div id="balance" style="font-weight:900">$0.00</div><div id="acct" class="badge demo">DEMO</div></div></div><div style="padding:12px;display:flex;gap:8px;flex-wrap:wrap"><button class="btn btn-red" onclick="api('/api/start')">Start</button><button class="btn btn-yellow" onclick="api('/api/pause')">Pause/Resume</button><button class="btn btn-grey" onclick="api('/api/stop')">Stop</button><button class="btn btn-grey" onclick="testConn()">Test Connection</button></div><div class="grid"><div class="panel"><h3>SETTINGS</h3>API Token <input id="token" type="password" placeholder="Paste Deriv token pat_...">Account <select id="acctype"><option selected>DEMO</option><option>REAL</option></select>Market <select id="market"><option value="R_10">V10</option><option value="R_25">V25</option><option value="R_50">V50</option><option value="R_75">V75</option><option value="R_100" selected>V100</option></select>Stake Mode <select id="stakemode"><option>Auto %</option><option>Fixed</option></select>Auto stake % <input id="autopct" type="number" value="1.5" step="0.1" max="2">Fixed stake <input id="fixed" type="number" value="1">Take Profit $ <input id="tp" type="number" value="3">Stop Loss $ <input id="sl" type="number" value="4">Trades/session <input id="tps" type="number" value="5">Min confidence % <input id="minconf" type="number" value="62"></div><div><div class="panel"><h3>LIVE STATS</h3><div class="stat"><span>Status</span><span id="status">WAITING</span></div><div class="stat"><span>Balance</span><span id="sbal">$0</span></div><div class="stat"><span>Profit Today</span><span id="pnl">$0</span></div><div class="stat"><span>Trades Today</span><span id="trades">0</span></div><div class="stat"><span>Win Rate</span><span id="wr">0%</span></div><div class="stat"><span>Session</span><span id="sess">1/3</span></div><div class="stat"><span>Last Scan</span><span id="scan">-</span></div></div><div class="panel" style="margin-top:12px"><h3>LOGS</h3><div id="log" class="log"></div></div></div></div><div style="text-align:center;padding:16px"><a href="https://app.deriv.com" target="_blank"><button class="btn btn-grey">View Transactions on Deriv</button></a><p style="font-size:10px;color:#666;margin-top:10px">Risk: Digits are random. Goal is capital protection, not 90-100% wins. Test on DEMO first.</p></div><script>let state={};async function refresh(){let r=await fetch('/api/state');state=await r.json();document.getElementById('status').innerText=state.status;document.getElementById('sbal').innerText='$'+state.balance.toFixed(2);document.getElementById('balance').innerText='$'+state.balance.toFixed(2)+' '+state.currency;document.getElementById('pnl').innerText='$'+state.profit_today.toFixed(2);document.getElementById('trades').innerText=state.trades_today;document.getElementById('wr').innerText=state.trades_today?Math.round(state.wins/state.trades_today*100)+'%':'0%';document.getElementById('sess').innerText=state.session+'/'+state.max_sessions+' ('+state.trades_in_session+')';document.getElementById('scan').innerText=`Even ${state.last_scan.even_pct}% / Over2 ${state.last_scan.over2_pct}% / Rare ${state.last_scan.rare_digit}`;document.getElementById('acct').innerText=state.is_demo?'DEMO':'REAL';document.getElementById('acct').className='badge '+(state.is_demo?'demo':'real');document.getElementById('log').innerText=state.logs.join('\\n');document.getElementById('log').scrollTop=99999;}async function api(url){let cfg={api_token:document.getElementById('token').value,account_type:document.getElementById('acctype').value,market:document.getElementById('market').value,stake_mode:document.getElementById('stakemode').value,auto_pct:parseFloat(document.getElementById('autopct').value),fixed_stake:parseFloat(document.getElementById('fixed').value),take_profit:parseFloat(document.getElementById('tp').value),stop_loss:parseFloat(document.getElementById('sl').value),trades_per_session:parseInt(document.getElementById('tps').value),min_confidence:parseInt(document.getElementById('minconf').value)};let r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(cfg)});let j=await r.json();alert(j.message||j.status);}async function testConn(){let r=await fetch('/api/test',{method:'POST'});let j=await r.json();alert(j.message);}setInterval(refresh,1000);refresh();</script></body></html>'''
@app.route("/api/state")
def api_state():
    return jsonify({"status": STATE["status"],"balance": STATE["balance"],"currency": STATE["currency"],"loginid": STATE["loginid"],"is_demo": STATE["is_demo"],"profit_today": STATE["profit_today"],"trades_today": STATE["trades_today"],"wins": STATE["wins"],"losses": STATE["losses"],"session": STATE["session"],"max_sessions": STATE["max_sessions"],"trades_in_session": STATE["trades_in_session"],"last_scan": STATE["last_scan"],"logs": list(STATE["logs"]),"paused": STATE["paused"],"running": STATE["running"]})
@app.route("/api/test", methods=["POST"])
def api_test():
    async def _test():
        start=time.time()
        try:
            async with websockets.connect(DERIV_WS_URL, open_timeout=15) as ws:
                await asyncio.wait_for(ws.send(json.dumps({"ping":1})), timeout=20)
                await asyncio.wait_for(ws.recv(), timeout=20)
                ms=int((time.time()-start)*1000)
                return True, f"Deriv reachable ({ms} ms)"
        except Exception as e:
            return False, f"Test failed: {e}"
    loop=asyncio.new_event_loop()
    ok,msg=loop.run_until_complete(_test())
    loop.close()
    return jsonify({"ok":ok,"message":msg})
@app.route("/api/start", methods=["POST"])
def api_start():
    global bot_thread, BOT_CONFIG
    data=request.get_json() or {}
    for k in BOT_CONFIG:
        if k in data: BOT_CONFIG[k]=data[k]
    if not BOT_CONFIG["api_token"]:
        return jsonify({"message":"Enter your Deriv API token first"})
    if STATE["running"]:
        return jsonify({"message":"Bot already running"})
    control_flags["stop"]=False
    control_flags["pause"]=False
    bot_thread=threading.Thread(target=run_bot_thread, daemon=True)
    bot_thread.start()
    return jsonify({"message":"Starting..."})
@app.route("/api/pause", methods=["POST"])
def api_pause():
    if not STATE["running"]: return jsonify({"message":"Bot not running"})
    control_flags["pause"]=not control_flags["pause"]
    STATE["paused"]=control_flags["pause"]
    set_status("PAUSED" if STATE["paused"] else "TRADING")
    return jsonify({"message":"Paused" if STATE["paused"] else "Resumed"})
@app.route("/api/stop", methods=["POST"])
def api_stop():
    control_flags["stop"]=True
    STATE["running"]=False
    set_status("STOPPED")
    return jsonify({"message":"Stopping..."})
def get_last_digit(price, pip_size):
    try:
        factor=10**pip_size
        return int(round((price*factor)%10))%10
    except: return 0
def scan_market():
    if len(ticks_buffer)<100: return None
    digits=list(ticks_buffer)
    even=sum(1 for d in digits if d%2==0)
    over2=sum(1 for d in digits if d>2)
    freq=Counter(digits)
    rarest_digit, rarest_count=freq.most_common()[-1]
    STATE["last_scan"]={"even_pct":round(even,1),"over2_pct":round(over2,1),"rare_digit":str(rarest_digit),"rare_freq":round(rarest_count,1)}
    return {"digits":digits,"even_pct":even,"over2_pct":over2,"freq":freq,"rarest":(rarest_digit,round(rarest_count,1))}
def calculate_confidence(scan):
    scores={}
    ep=scan["even_pct"]
    if ep<45: scores["ODD"]=min(95,int((45-ep)*3+50))
    elif ep>55: scores["EVEN"]=min(95,int((ep-55)*3+50))
    op=scan["over2_pct"]
    if op<62: scores["OVER2"]=min(90,int((62-op)*2+40))
    rarest_digit, rare_pct=scan["rarest"]
    if rare_pct<4: scores[f"MATCH_{rarest_digit}"]=min(85,int((4-rare_pct)*15+60))
    return scores
async def connect_ws(url, token):
    set_status("OPENING SOCKET")
    try:
        ws=await asyncio.wait_for(websockets.connect(url), timeout=15)
        set_status("SOCKET OPEN")
        set_status("AUTHORIZING")
        await asyncio.wait_for(ws.send(json.dumps({"authorize":token})), timeout=20)
        raw=await asyncio.wait_for(ws.recv(), timeout=20)
        resp=json.loads(raw)
        if "error" in resp:
            err=resp["error"].get("message",str(resp["error"]))
            set_status("STOPPED")
            await ws.close()
            return None, err
        loginid=resp.get("authorize",{}).get("loginid","")
        is_demo="demo" in loginid.lower() or "VRTC" in loginid
        wants_demo=BOT_CONFIG["account_type"]=="DEMO"
        if wants_demo and not is_demo:
            set_status("STOPPED"); await ws.close(); return None, f"DEMO selected but token is REAL ({loginid})"
        if not wants_demo and is_demo:
            set_status("STOPPED"); await ws.close(); return None, f"REAL selected but token is DEMO ({loginid})"
        STATE["loginid"]=loginid; STATE["is_demo"]=is_demo; STATE["currency"]=resp.get("authorize",{}).get("currency","USD")
        await asyncio.wait_for(ws.send(json.dumps({"balance":1})), timeout=20)
        br=json.loads(await asyncio.wait_for(ws.recv(), timeout=20))
        if "balance" in br: STATE["balance"]=float(br["balance"].get("balance",0))
        log_msg(f"AUTHORIZED {loginid} Balance ${STATE['balance']}")
        set_status("SUBSCRIBING")
        return ws, None
    except Exception as e:
        log_msg(f"Connect failed: {e}"); set_status("RECONNECTING"); return None, str(e)
def check_risk(stake):
    bal=STATE["balance"]
    if bal<=0: return False, "Balance zero"
    if STATE["profit_today"]>=BOT_CONFIG["take_profit"]: set_status("DAY LIMIT"); return False, "Take Profit hit"
    if STATE["profit_today"]<=-BOT_CONFIG["stop_loss"]: set_status("DAY LIMIT"); return False, "Stop Loss hit"
    if STATE["trades_in_session"]>=BOT_CONFIG["trades_per_session"]: set_status("SESSION BREAK"); return False, "Session limit"
    if STATE["session"]>STATE["max_sessions"]: set_status("DAY LIMIT"); return False, "Max sessions"
    if stake<0.35: set_status("STOPPED"); return False, f"Stake ${stake:.2f} below minimum $0.35"
    return True, "ok"
async def place_trade(ws, setup, stake, market):
    cmap={"EVEN":"DIGITEVEN","ODD":"DIGITODD","OVER2":"DIGITOVER"}
    ctype=cmap.get(setup,None); barrier=None
    if setup.startswith("MATCH_"): ctype="DIGITMATCH"; barrier=setup.split("_")[1]
    prop={"proposal":1,"amount":stake,"basis":"stake","contract_type":ctype,"currency":STATE["currency"],"duration":1,"duration_unit":"t","symbol":market}
    if ctype=="DIGITOVER": prop["barrier"]=2
    if barrier is not None: prop["barrier"]=int(barrier)
    try:
        await asyncio.wait_for(ws.send(json.dumps(prop)), timeout=20)
        resp=json.loads(await asyncio.wait_for(ws.recv(), timeout=20))
        if "error" in resp: log_msg(f"Proposal error: {resp['error'].get('message')}"); return None
        pid=resp.get("proposal",{}).get("id")
        if not pid: return None
        await asyncio.wait_for(ws.send(json.dumps({"buy":pid,"price":stake})), timeout=20)
        buy=json.loads(await asyncio.wait_for(ws.recv(), timeout=20))
        if "error" in buy: log_msg(f"Buy error: {buy['error'].get('message')}"); return None
        cid=buy.get("buy",{}).get("contract_id")
        log_msg(f"BOUGHT {setup} {market} ${stake} ID {cid}")
        return cid
    except Exception as e:
        log_msg(f"place_trade failed: {e}"); return None
async def trading_loop():
    retry=3
    last_day=datetime.now(timezone.utc).date()
    while not control_flags["stop"]:
        try:
            if control_flags["pause"]: set_status("PAUSED"); await asyncio.sleep(1); continue
            today=datetime.now(timezone.utc).date()
            if today!=last_day:
                STATE["profit_today"]=0; STATE["trades_today"]=0; STATE["wins"]=0; STATE["losses"]=0; STATE["session"]=1; STATE["trades_in_session"]=0; last_day=today; log_msg("Midnight GMT reset")
            ws,err=await connect_ws(DERIV_WS_URL, BOT_CONFIG["api_token"])
            if not ws:
                log_msg(f"RECONNECTING in {retry}s: {err}"); await asyncio.sleep(retry); retry=min(60,retry+3); continue
            retry=3
            ticks_buffer.clear()
            set_status("SCANNING (0/100)")
            await ws.send(json.dumps({"ticks":BOT_CONFIG["market"],"subscribe":1}))
            log_msg(f"SUBSCRIBING {BOT_CONFIG['market']}")
            while not control_flags["stop"] and not control_flags["pause"]:
                try:
                    raw=await asyncio.wait_for(ws.recv(), timeout=20)
                    data=json.loads(raw)
                    if "error" in data: log_msg(f"API error: {data['error'].get('message')}"); continue
                    if "tick" in data:
                        tick=data["tick"]; price=tick.get("quote"); pip=tick.get("pip_size",2)
                        ticks_buffer.append(get_last_digit(price,pip))
                        cnt=len(ticks_buffer)
                        if cnt%20==0 or cnt==100: set_status(f"SCANNING ({cnt}/100)")
                        if cnt<100: continue
                        scan=scan_market()
                        if not scan: continue
                        scores=calculate_confidence(scan)
                        if not scores: set_status(f"SCANNING ({cnt}/100) - No setup"); continue
                        best=max(scores,key=lambda k:scores[k]); conf=scores[best]
                        log_msg(f"SCAN Even {scan['even_pct']}% Over2 {scan['over2_pct']}% Rare {scan['rarest'][0]} {scan['rarest'][1]}% | Best {best} {conf}%")
                        if conf<BOT_CONFIG["min_confidence"]: continue
                        bal=STATE["balance"]
                        stake=round(bal*min(BOT_CONFIG["auto_pct"],2.0)/100,2) if BOT_CONFIG["stake_mode"]=="Auto %" else float(BOT_CONFIG["fixed_stake"])
                        if best.startswith("MATCH_"): stake=round(stake*0.5,2)
                        ok,reason=check_risk(stake)
                        if not ok:
                            log_msg(f"Risk bloc# ALGOSPHERE by TEXXADURK - Complete
import os, sys, time, json, base64, asyncio, threading
from datetime import datetime, timezone
from collections import Counter, deque
try:
    import websockets
except ImportError:
    print("Missing package: pip install websockets flask python-telegram-bot")
    sys.exit(1)
from flask import Flask, request, jsonify, Response
DERIV_WS_URL = os.getenv("DERIV_WS_URL", "wss://ws.derivws.com/websockets/v3?app_id=1089")
PORT = int(os.getenv("PORT", "3000"))
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "9271580025:AAE0lGxG5qbBIvcm-wyz8UOgdOT_Wi-0nWo")
app = Flask(__name__)
STATE = {"status": "WAITING FOR SETUP","balance": 0.0, "currency": "USD", "loginid": "", "is_demo": True, "profit_today": 0.0, "trades_today": 0,"wins": 0, "losses": 0, "session": 1, "max_sessions": 3,"trades_in_session": 0,"last_scan": {"even_pct": 0, "over2_pct": 0, "rare_digit": "-", "rare_freq": 0},"logs": deque(maxlen=150), "paused": False, "running": False,}
BOT_CONFIG = {"api_token": "","account_type": "DEMO", "market": "R_100", "stake_mode": "Auto %","auto_pct": 1.5, "fixed_stake": 1.0, "take_profit": 3.0, "stop_loss": 4.0,"trades_per_session": 5, "min_confidence": 62,}
bot_thread = None
control_flags = {"stop": False, "pause": False}
ticks_buffer = deque(maxlen=100)
LOGO_SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="60" height="60" viewBox="0 0 60 60"><circle cx="30" cy="30" r="28" fill="#0A0A0A" stroke="#FF0033" stroke-width="1.5"/><circle cx="30" cy="30" r="14" fill="black" stroke="#FF0033" stroke-width="1"/><text x="30" y="35" text-anchor="middle" font-family="Orbitron" font-weight="900" font-size="16" fill="#FF0033">A</text></svg>'
def log_msg(msg):
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    line = f"[{ts} GMT] {msg}"
    STATE["logs"].append(line)
    print(line, flush=True)
def set_status(s):
    STATE["status"] = s
    log_msg(f"STATUS: {s}")
@app.route("/logo.svg")
def logo():
    return Response(LOGO_SVG, mimetype="image/svg+xml")
@app.route("/")
def store():
    return '''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ALGOSPHERE</title><link rel="icon" href="/logo.svg"><link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&display=swap" rel="stylesheet"><style>body{background:#0A0A0A;color:white;font-family:monospace;margin:0}h1{font-family:Orbitron}.hero{text-align:center;padding:60px 20px}.btn{background:#FF0033;color:black;font-family:Orbitron;font-weight:900;padding:18px 36px;border:none;clip-path:polygon(10% 0,100% 0,90% 100%,0 100%);cursor:pointer;font-size:18px}.btn:hover{box-shadow:0 0 25px #FF0033}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;max-width:900px;margin:30px auto;padding:0 20px}.card{border:1px solid #222;padding:20px;background:#111}.accent{color:#FF0033}.warn{color:#888;font-size:12px;text-align:center;margin:40px}</style></head><body><div class="hero"><img src="/logo.svg" width="80"><h1 style="font-size:42px">ALGOSPHERE</h1><div class="accent" style="font-family:Orbitron">by TEXXADURK</div><p>Disciplined digit-trading bot for Deriv. Capital protection first.</p><a href="/dashboard"><button class="btn">OPEN BOT</button></a></div><div class="cards"><div class="card"><b class="accent">Safe risk limits</b><br><small>Auto 1.5% max 2%, daily +$3 / -$4 stop.</small></div><div class="card"><b class="accent">No recovery</b><br><small>Never martingale.</small></div><div class="card"><b class="accent">Live dashboard</b><br><small>100-tick scan, confidence scoring.</small></div><div class="card"><b class="accent">Demo-first</b><br><small>Test on DEMO before REAL.</small></div></div><div class="warn">Risk: Trading involves risk. Digit results are random. Goal is capital protection, not guaranteed wins. Test on DEMO first.</div></body></html>'''
@app.route("/dashboard")
def dashboard():
    return '''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ALGOSPHERE Dashboard</title><link rel="icon" href="/logo.svg"><link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&display=swap" rel="stylesheet"><style>:root{--bg:#0A0A0A;--red:#FF0033;--yellow:#FFE600;--grey:#1A1A1A}body{background:var(--bg);color:white;font-family:monospace;margin:0}.top{display:flex;justify-content:space-between;align-items:center;padding:12px 16px;border-bottom:1px solid #222;background:#0F0F0F}h1{font-family:Orbitron;margin:0;font-size:22px}small.red{color:var(--red);font-family:Orbitron;font-size:10px}.badge{padding:4px 10px;border:1px solid #333;font-size:12px}.badge.demo{color:var(--yellow);border-color:var(--yellow)}.badge.real{color:var(--red);border-color:var(--red)}.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;padding:12px}@media(max-width:700px){.grid{grid-template-columns:1fr}}.panel{background:var(--grey);border:1px solid #222;padding:14px}.panel h3{font-family:Orbitron;font-size:12px;margin:0 0 10px;color:var(--red)}input,select{width:100%;background:black;color:white;border:1px solid #333;padding:8px;margin:4px 0;font-family:monospace}.btn{font-family:Orbitron;font-weight:900;padding:12px 20px;border:none;cursor:pointer;clip-path:polygon(8% 0,100% 0,92% 100%,0 100%);margin:4px}.btn-red{background:var(--red);color:black}.btn-yellow{background:var(--yellow);color:black}.btn-grey{background:#333;color:white}.log{height:280px;overflow-y:auto;background:black;color:var(--red);font-size:11px;padding:8px;border:1px solid #222;white-space:pre-wrap}.stat{display:flex;justify-content:space-between;font-size:12px;padding:4px 0;border-bottom:1px dashed #222}</style></head><body><div class="top"><div style="display:flex;align-items:center;gap:10px"><img src="/logo.svg" width="44"><div><h1>ALGOSPHERE</h1><small class="red">by TEXXADURK</small></div></div><div style="text-align:right"><div id="balance" style="font-weight:900">$0.00</div><div id="acct" class="badge demo">DEMO</div></div></div><div style="padding:12px;display:flex;gap:8px;flex-wrap:wrap"><button class="btn btn-red" onclick="api('/api/start')">Start</button><button class="btn btn-yellow" onclick="api('/api/pause')">Pause/Resume</button><button class="btn btn-grey" onclick="api('/api/stop')">Stop</button><button class="btn btn-grey" onclick="testConn()">Test Connection</button></div><div class="grid"><div class="panel"><h3>SETTINGS</h3>API Token <input id="token" type="password" placeholder="Paste Deriv token pat_...">Account <select id="acctype"><option selected>DEMO</option><option>REAL</option></select>Market <select id="market"><option value="R_10">V10</option><option value="R_25">V25</option><option value="R_50">V50</option><option value="R_75">V75</option><option value="R_100" selected>V100</option></select>Stake Mode <select id="stakemode"><option>Auto %</option><option>Fixed</option></select>Auto stake % <input id="autopct" type="number" value="1.5" step="0.1" max="2">Fixed stake <input id="fixed" type="number" value="1">Take Profit $ <input id="tp" type="number" value="3">Stop Loss $ <input id="sl" type="number" value="4">Trades/session <input id="tps" type="number" value="5">Min confidence % <input id="minconf" type="number" value="62"></div><div><div class="panel"><h3>LIVE STATS</h3><div class="stat"><span>Status</span><span id="status">WAITING</span></div><div class="stat"><span>Balance</span><span id="sbal">$0</span></div><div class="stat"><span>Profit Today</span><span id="pnl">$0</span></div><div class="stat"><span>Trades Today</span><span id="trades">0</span></div><div class="stat"><span>Win Rate</span><span id="wr">0%</span></div><div class="stat"><span>Session</span><span id="sess">1/3</span></div><div class="stat"><span>Last Scan</span><span id="scan">-</span></div></div><div class="panel" style="margin-top:12px"><h3>LOGS</h3><div id="log" class="log"></div></div></div></div><div style="text-align:center;padding:16px"><a href="https://app.deriv.com" target="_blank"><button class="btn btn-grey">View Transactions on Deriv</button></a><p style="font-size:10px;color:#666;margin-top:10px">Risk: Digits are random. Goal is capital protection, not 90-100% wins. Test on DEMO first.</p></div><script>let state={};async function refresh(){let r=await fetch('/api/state');state=await r.json();document.getElementById('status').innerText=state.status;document.getElementById('sbal').innerText='$'+state.balance.toFixed(2);document.getElementById('balance').innerText='$'+state.balance.toFixed(2)+' '+state.currency;document.getElementById('pnl').innerText='$'+state.profit_today.toFixed(2);document.getElementById('trades').innerText=state.trades_today;document.getElementById('wr').innerText=state.trades_today?Math.round(state.wins/state.trades_today*100)+'%':'0%';document.getElementById('sess').innerText=state.session+'/'+state.max_sessions+' ('+state.trades_in_session+')';document.getElementById('scan').innerText=`Even ${state.last_scan.even_pct}% / Over2 ${state.last_scan.over2_pct}% / Rare ${state.last_scan.rare_digit}`;document.getElementById('acct').innerText=state.is_demo?'DEMO':'REAL';document.getElementById('acct').className='badge '+(state.is_demo?'demo':'real');document.getElementById('log').innerText=state.logs.join('\\n');document.getElementById('log').scrollTop=99999;}async function api(url){let cfg={api_token:document.getElementById('token').value,account_type:document.getElementById('acctype').value,market:document.getElementById('market').value,stake_mode:document.getElementById('stakemode').value,auto_pct:parseFloat(document.getElementById('autopct').value),fixed_stake:parseFloat(document.getElementById('fixed').value),take_profit:parseFloat(document.getElementById('tp').value),stop_loss:parseFloat(document.getElementById('sl').value),trades_per_session:parseInt(document.getElementById('tps').value),min_confidence:parseInt(document.getElementById('minconf').value)};let r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(cfg)});let j=await r.json();alert(j.message||j.status);}async function testConn(){let r=await fetch('/api/test',{method:'POST'});let j=await r.json();alert(j.message);}setInterval(refresh,1000);refresh();</script></body></html>'''
@app.route("/api/state")
def api_state():
    return jsonify({"status": STATE["status"],"balance": STATE["balance"],"currency": STATE["currency"],"loginid": STATE["loginid"],"is_demo": STATE["is_demo"],"profit_today": STATE["profit_today"],"trades_today": STATE["trades_today"],"wins": STATE["wins"],"losses": STATE["losses"],"session": STATE["session"],"max_sessions": STATE["max_sessions"],"trades_in_session": STATE["trades_in_session"],"last_scan": STATE["last_scan"],"logs": list(STATE["logs"]),"paused": STATE["paused"],"running": STATE["running"]})
@app.route("/api/test", methods=["POST"])
def api_test():
    async def _test():
        start=time.time()
        try:
            async with websockets.connect(DERIV_WS_URL, open_timeout=15) as ws:
                await asyncio.wait_for(ws.send(json.dumps({"ping":1})), timeout=20)
                await asyncio.wait_for(ws.recv(), timeout=20)
                ms=int((time.time()-start)*1000)
                return True, f"Deriv reachable ({ms} ms)"
        except Exception as e:
            return False, f"Test failed: {e}"
    loop=asyncio.new_event_loop()
    ok,msg=loop.run_until_complete(_test())
    loop.close()
    return jsonify({"ok":ok,"message":msg})
@app.route("/api/start", methods=["POST"])
def api_start():
    global bot_thread, BOT_CONFIG
    data=request.get_json() or {}
    for k in BOT_CONFIG:
        if k in data: BOT_CONFIG[k]=data[k]
    if not BOT_CONFIG["api_token"]:
        return jsonify({"message":"Enter your Deriv API token first"})
    if STATE["running"]:
        return jsonify({"message":"Bot already running"})
    control_flags["stop"]=False
    control_flags["pause"]=False
    bot_thread=threading.Thread(target=run_bot_thread, daemon=True)
    bot_thread.start()
    return jsonify({"message":"Starting..."})
@app.route("/api/pause", methods=["POST"])
def api_pause():
    if not STATE["running"]: return jsonify({"message":"Bot not running"})
    control_flags["pause"]=not control_flags["pause"]
    STATE["paused"]=control_flags["pause"]
    set_status("PAUSED" if STATE["paused"] else "TRADING")
    return jsonify({"message":"Paused" if STATE["paused"] else "Resumed"})
@app.route("/api/stop", methods=["POST"])
def api_stop():
    control_flags["stop"]=True
    STATE["running"]=False
    set_status("STOPPED")
    return jsonify({"message":"Stopping..."})
def get_last_digit(price, pip_size):
    try:
        factor=10**pip_size
        return int(round((price*factor)%10))%10
    except: return 0
def scan_market():
    if len(ticks_buffer)<100: return None
    digits=list(ticks_buffer)
    even=sum(1 for d in digits if d%2==0)
    over2=sum(1 for d in digits if d>2)
    freq=Counter(digits)
    rarest_digit, rarest_count=freq.most_common()[-1]
    STATE["last_scan"]={"even_pct":round(even,1),"over2_pct":round(over2,1),"rare_digit":str(rarest_digit),"rare_freq":round(rarest_count,1)}
    return {"digits":digits,"even_pct":even,"over2_pct":over2,"freq":freq,"rarest":(rarest_digit,round(rarest_count,1))}
def calculate_confidence(scan):
    scores={}
    ep=scan["even_pct"]
    if ep<45: scores["ODD"]=min(95,int((45-ep)*3+50))
    elif ep>55: scores["EVEN"]=min(95,int((ep-55)*3+50))
    op=scan["over2_pct"]
    if op<62: scores["OVER2"]=min(90,int((62-op)*2+40))
    rarest_digit, rare_pct=scan["rarest"]
    if rare_pct<4: scores[f"MATCH_{rarest_digit}"]=min(85,int((4-rare_pct)*15+60))
    return scores
async def connect_ws(url, token):
    set_status("OPENING SOCKET")
    try:
        ws=await asyncio.wait_for(websockets.connect(url), timeout=15)
        set_status("SOCKET OPEN")
        set_status("AUTHORIZING")
        await asyncio.wait_for(ws.send(json.dumps({"authorize":token})), timeout=20)
        raw=await asyncio.wait_for(ws.recv(), timeout=20)
        resp=json.loads(raw)
        if "error" in resp:
            err=resp["error"].get("message",str(resp["error"]))
            set_status("STOPPED")
            await ws.close()
            return None, err
        loginid=resp.get("authorize",{}).get("loginid","")
        is_demo="demo" in loginid.lower() or "VRTC" in loginid
        wants_demo=BOT_CONFIG["account_type"]=="DEMO"
        if wants_demo and not is_demo:
            set_status("STOPPED"); await ws.close(); return None, f"DEMO selected but token is REAL ({loginid})"
        if not wants_demo and is_demo:
            set_status("STOPPED"); await ws.close(); return None, f"REAL selected but token is DEMO ({loginid})"
        STATE["loginid"]=loginid; STATE["is_demo"]=is_demo; STATE["currency"]=resp.get("authorize",{}).get("currency","USD")
        await asyncio.wait_for(ws.send(json.dumps({"balance":1})), timeout=20)
        br=json.loads(await asyncio.wait_for(ws.recv(), timeout=20))
        if "balance" in br: STATE["balance"]=float(br["balance"].get("balance",0))
        log_msg(f"AUTHORIZED {loginid} Balance ${STATE['balance']}")
        set_status("SUBSCRIBING")
        return ws, None
    except Exception as e:
        log_msg(f"Connect failed: {e}"); set_status("RECONNECTING"); return None, str(e)
def check_risk(stake):
    bal=STATE["balance"]
    if bal<=0: return False, "Balance zero"
    if STATE["profit_today"]>=BOT_CONFIG["take_profit"]: set_status("DAY LIMIT"); return False, "Take Profit hit"
    if STATE["profit_today"]<=-BOT_CONFIG["stop_loss"]: set_status("DAY LIMIT"); return False, "Stop Loss hit"
    if STATE["trades_in_session"]>=BOT_CONFIG["trades_per_session"]: set_status("SESSION BREAK"); return False, "Session limit"
    if STATE["session"]>STATE["max_sessions"]: set_status("DAY LIMIT"); return False, "Max sessions"
    if stake<0.35: set_status("STOPPED"); return False, f"Stake ${stake:.2f} below minimum $0.35"
    return True, "ok"
async def place_trade(ws, setup, stake, market):
    cmap={"EVEN":"DIGITEVEN","ODD":"DIGITODD","OVER2":"DIGITOVER"}
    ctype=cmap.get(setup,None); barrier=None
    if setup.startswith("MATCH_"): ctype="DIGITMATCH"; barrier=setup.split("_")[1]
    prop={"proposal":1,"amount":stake,"basis":"stake","contract_type":ctype,"currency":STATE["currency"],"duration":1,"duration_unit":"t","symbol":market}
    if ctype=="DIGITOVER": prop["barrier"]=2
    if barrier is not None: prop["barrier"]=int(barrier)
    try:
        await asyncio.wait_for(ws.send(json.dumps(prop)), timeout=20)
        resp=json.loads(await asyncio.wait_for(ws.recv(), timeout=20))
        if "error" in resp: log_msg(f"Proposal error: {resp['error'].get('message')}"); return None
        pid=resp.get("proposal",{}).get("id")
        if not pid: return None
        await asyncio.wait_for(ws.send(json.dumps({"buy":pid,"price":stake})), timeout=20)
        buy=json.loads(await asyncio.wait_for(ws.recv(), timeout=20))
        if "error" in buy: log_msg(f"Buy error: {buy['error'].get('message')}"); return None
        cid=buy.get("buy",{}).get("contract_id")
        log_msg(f"BOUGHT {setup} {market} ${stake} ID {cid}")
        return cid
    except Exception as e:
        log_msg(f"place_trade failed: {e}"); return None
async def trading_loop():
    retry=3
    last_day=datetime.now(timezone.utc).date()
    while not control_flags["stop"]:
        try:
            if control_flags["pause"]: set_status("PAUSED"); await asyncio.sleep(1); continue
            today=datetime.now(timezone.utc).date()
            if today!=last_day:
                STATE["profit_today"]=0; STATE["trades_today"]=0; STATE["wins"]=0; STATE["losses"]=0; STATE["session"]=1; STATE["trades_in_session"]=0; last_day=today; log_msg("Midnight GMT reset")
            ws,err=await connect_ws(DERIV_WS_URL, BOT_CONFIG["api_token"])
            if not ws:
                log_msg(f"RECONNECTING in {retry}s: {err}"); await asyncio.sleep(retry); retry=min(60,retry+3); continue
            retry=3
            ticks_buffer.clear()
            set_status("SCANNING (0/100)")
            await ws.send(json.dumps({"ticks":BOT_CONFIG["market"],"subscribe":1}))
            log_msg(f"SUBSCRIBING {BOT_CONFIG['market']}")
            while not control_flags["stop"] and not control_flags["pause"]:
                try:
                    raw=await asyncio.wait_for(ws.recv(), timeout=20)
                    data=json.loads(raw)
                    if "error" in data: log_msg(f"API error: {data['error'].get('message')}"); continue
                    if "tick" in data:
                        tick=data["tick"]; price=tick.get("quote"); pip=tick.get("pip_size",2)
                        ticks_buffer.append(get_last_digit(price,pip))
                        cnt=len(ticks_buffer)
                        if cnt%20==0 or cnt==100: set_status(f"SCANNING ({cnt}/100)")
                        if cnt<100: continue
                        scan=scan_market()
                        if not scan: continue
                        scores=calculate_confidence(scan)
                        if not scores: set_status(f"SCANNING ({cnt}/100) - No setup"); continue
                        best=max(scores,key=lambda k:scores[k]); conf=scores[best]
                        log_msg(f"SCAN Even {scan['even_pct']}% Over2 {scan['over2_pct']}% Rare {scan['rarest'][0]} {scan['rarest'][1]}% | Best {best} {conf}%")
                        if conf<BOT_CONFIG["min_confidence"]: continue
                        bal=STATE["balance"]
                        stake=round(bal*min(BOT_CONFIG["auto_pct"],2.0)/100,2) if BOT_CONFIG["stake_mode"]=="Auto %" else float(BOT_CONFIG["fixed_stake"])
                        if best.startswith("MATCH_"): stake=round(stake*0.5,2)
                        ok,reason=check_risk(stake)
                        if not ok:
                            log_msg(f"Risk bloc
