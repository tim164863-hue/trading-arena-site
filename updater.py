#!/usr/bin/env python3
"""TRADING ARENA updater — READ-ONLY OKX v5 endpoints. Never places orders.
Env: OKX_API_KEY_1 / OKX_SECRET_1 / OKX_PASSPHRASE_1 (交易員-1), same with _2 (交易員-2).
Optional: START_EQUITY (default 100), LOOP_SECONDS (0 = run once).
Traders without keys are reported as status "offline" (未連線) with no data. No fake data is ever generated."""
import os, json, time, hmac, hashlib, base64, datetime, urllib.request, urllib.parse
BASE = "https://www.okx.com"; DIR = os.path.dirname(os.path.abspath(__file__))
TZ = datetime.timezone(datetime.timedelta(hours=8)); START = float(os.getenv("START_EQUITY", "100"))
NAMES = ["交易員-1", "交易員-2"]

def creds(i):
    g = os.getenv
    k, s, p = g(f"OKX_API_KEY_{i}"), g(f"OKX_SECRET_{i}"), g(f"OKX_PASSPHRASE_{i}")
    return (k, s, p) if k and s and p else None

def get(c, path, params=None):
    q = ("?" + urllib.parse.urlencode(params)) if params else ""
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    sig = base64.b64encode(hmac.new(c[1].encode(), (ts + "GET" + path + q).encode(), hashlib.sha256).digest()).decode()
    r = urllib.request.Request(BASE + path + q, headers={"OK-ACCESS-KEY": c[0], "OK-ACCESS-SIGN": sig,
        "OK-ACCESS-TIMESTAMP": ts, "OK-ACCESS-PASSPHRASE": c[2], "Content-Type": "application/json", "User-Agent": "arena-updater/1.0"})
    d = json.load(urllib.request.urlopen(r, timeout=15))
    if d.get("code") != "0": raise RuntimeError(f"{path}: {d.get('code')} {d.get('msg')}")
    return d["data"]

def tstr(ms): return datetime.datetime.fromtimestamp(int(ms) / 1000, TZ).strftime("%Y-%m-%d %H:%M:%S")

def real(name, c):
    eq = float(get(c, "/api/v5/account/balance", {"ccy": "USDT"})[0].get("totalEq") or 0)
    pos = [{"inst": p["instId"], "instId": p["instId"], "side": "long" if p.get("posSide") == "long" or (p.get("posSide") == "net" and float(p["pos"]) > 0) else "short",
            "sz": str(abs(float(p["pos"]))), "pos": p["pos"], "avgPx": p["avgPx"], "markPx": p.get("markPx"), "upl": p.get("upl")}
           for p in get(c, "/api/v5/account/positions") if float(p.get("pos") or 0) != 0]
    fills = []
    for path in ("/api/v5/trade/fills-history",):
        after = None
        for _ in range(10):
            prm = {"instType": "SWAP", "limit": "100"}
            if after: prm["after"] = after
            b = get(c, path, prm)
            if not b: break
            fills += b; after = b[-1]["billId"]
            if len(b) < 100: break
    fee_total = sum(float(f.get("fee") or 0) for f in fills)
    funding = sum(float(b.get("balChg") or 0) for b in get(c, "/api/v5/account/bills", {"type": "8", "limit": "100"}))
    trades = []
    for f in fills:
        sd, ps = f.get("side"), f.get("posSide")
        if ps == "long": lab = "開多" if sd == "buy" else "平多"
        elif ps == "short": lab = "開空" if sd == "sell" else "平空"
        else: lab = "買入" if sd == "buy" else "賣出"
        pnl = float(f.get("fillPnl") or 0) + float(f.get("fee") or 0)
        trades.append({"trader": name, "time": tstr(f["ts"]), "market": f["instId"], "side": lab, "price": f["fillPx"],
                       "qty": f"{f['fillSz']} 張", "pnl": round(pnl, 4), "note": f"手續費 {f.get('fee')}", "fee": float(f.get("fee") or 0)})
    return {"start": START, "equity": eq, "positions": pos, "fees_total": fee_total, "fills_total": len(fills),
            "funding_total": funding, "status": "live" if fills else "waiting"}, trades

def offline(status="offline"):
    return {"start": START, "equity": None, "positions": [], "fees_total": None, "fills_total": 0,
            "funding_total": None, "status": status}, []

def run():
    traders, trades, errors = {}, [], []
    for i, n in enumerate(NAMES, 1):
        c = creds(i)
        try:
            t, tr = real(n, c) if c else offline()
        except Exception as e:
            errors.append(f"{n}: {e}"); t, tr = offline("error")
        traders[n] = t; trades += tr
    trades.sort(key=lambda x: x["time"]); trades = trades[-200:]
    data = {"traders": traders, "trades": trades,             "updated": int(time.time() * 1000), "errors": errors}
    hp = os.path.join(DIR, "history.json")
    try: H = json.load(open(hp))
    except Exception: H = {}
    now = int(time.time() * 1000)
    for n, t in traders.items():
        p = H.setdefault(n, [])
        if t["status"] not in ("live", "waiting") or t["equity"] is None: continue
        p.append([now, round(t["equity"], 3)]); H[n] = p[-3000:]
    for fn, obj in (("data.json", data), ("history.json", H)):
        tmp = os.path.join(DIR, fn + ".tmp"); json.dump(obj, open(tmp, "w"), ensure_ascii=False); os.replace(tmp, os.path.join(DIR, fn))
    print(time.strftime("%F %T"), "ok", {n: t["status"] for n, t in traders.items()}, errors)

if __name__ == "__main__":
    loop = int(os.getenv("LOOP_SECONDS", "0"))
    while True:
        run()
        if not loop: break
        time.sleep(loop)
