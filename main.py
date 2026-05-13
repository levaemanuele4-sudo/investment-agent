import os, yfinance as yf, requests, numpy as np, datetime, math

# --- CONFIGURAZIONE HARD CODED PER TEST ---
# Quote approssimative per VT (Azionario) e AGG (Obbligazionario)
H_VWCE = 40.0  
H_IBTM = 15.0  
CAPITAL = 5000.0
INFLATION = 0.025
TG_TOKEN = "8876010394:AAHK3wjlNm2DQfPDt1pgkPM73bTBjXmZa3A"
TG_CHAT = "1103185363"
GROQ_KEY = "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"

def fetch_data():
    try:
        # Usiamo VT (Vanguard Total World) e AGG (Aggregate Bond) che sono molto liquidi
        print("Scaricando dati per VT...")
        v = yf.Ticker("VT").history(period="6mo")["Close"]
        
        print("Scaricando dati per AGG...")
        i = yf.Ticker("AGG").history(period="6mo")["Close"]
        
        # Allinea le date comuni
        common = v.index.intersection(i.index)
        
        if len(common) < 10:
            print(f"Errore: Solo {len(common)} giorni di dati sovrapposti.")
            return None, None
            
        print(f"OK: Scaricati {len(common)} giorni di dati.")
        return v[common], i[common]
        
    except Exception as e:
        print(f"ERRORE CRITICO download dati: {e}")
        import traceback
        traceback.print_exc()
        return None, None

def calc_metrics(v, i):
    port = (v * H_VWCE) + (i * H_IBTM)
    if len(port) < 10:
        print("Dati insufficienti per calcolo metriche")
        return None
    
    cur = port.iloc[-1]
    days = (port.index[-1] - port.index[0]).days or 1
    
    # Calcoli base
    ret = (cur / CAPITAL) - 1
    # Evita errori matematici se days è piccolo o negativo
    if days <= 0: days = 1 
    cagr = (1 + ret) ** (365/days) - 1
    real_cagr = (1 + cagr) / (1 + INFLATION) - 1
    
    daily_ret = port.pct_change().dropna()
    vol = daily_ret.std() * np.sqrt(252)
    
    peak = port.expanding().max()
    max_dd = ((port - peak) / peak).min()
    
    sharpe = (cagr - 0.03) / vol if vol > 0 else 0
    
    return {
        "val": round(cur, 2), 
        "ret": round(ret*100, 2),
        "cagr": round(real_cagr*100, 2), 
        "vol": round(vol*100, 2),
        "dd": round(max_dd*100, 2), 
        "sharpe": round(sharpe, 2),
        "days": days
    }

def ai_report(m):
    prompt = f"""Sei un analista finanziario socratico.
Dati: Valore {m['val']} | Rend.Reale {m['cagr']}% | Vol {m['vol']}% | MaxDD {m['dd']}% | Sharpe {m['sharpe']}
Genera un report brevissimo (3 righe): 1) Sintesi 2) Rischio 3) Domanda socratica."""
    
    try:
        res = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
            json={"model": "llama-3.1-8b-instant", "messages": [{"role": "user", "content": prompt}], "max_tokens": 150, "temperature": 0.3}
        )
        return res.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Errore AI: {e}")
        return "⚠️ AI offline."

def send(msg):
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        payload = {"chat_id": TG_CHAT, "text": msg, "parse_mode": "Markdown"}
        r = requests.post(url, json=payload)
        print(f"Telegram Status: {r.status_code}")
    except Exception as e:
        print(f"Errore Telegram: {e}")

def main():
    print("Avvio bot...")
    v, i = fetch_data()
    
    if v is None:
        send("❌ Errore download dati di mercato. Controlla i log.")
        return
        
    m = calc_metrics(v, i)
    if not m:
        send("⏳ Dati insufficienti (serve più storico).")
        return
        
    ai_text = ai_report(m)
    
    msg = f"📊 *Report Portafoglio*\n\n"
    msg += f"💰 Valore: *{m['val']}*\n"
    msg += f"📈 Reale: *{m['cagr']}%* | Vol: *{m['vol']}%*\n"
    msg += f"📉 Drawdown: *{m['dd']}%*\n\n"
    msg += f"🤖 *AI:* {ai_text}"
    
    send(msg)
    print("✅ Inviato")

if __name__ == "__main__":
    main()
