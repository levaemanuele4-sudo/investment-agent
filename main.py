import os, yfinance as yf, requests, numpy as np, datetime, math

# CONFIGURAZIONE (legge da GitHub Secrets)
VWCE = "VWCE.MI"
IBTM = "IBTM.MI"
H_VWCE = float(os.getenv("HOLDINGS_VWCE", 35.0))
H_IBTM = float(os.getenv("HOLDINGS_IBTM", 8.0))
CAPITAL = float(os.getenv("INITIAL_CAPITAL", 5000.0))
INFLATION = float(os.getenv("INFLATION_RATE", 0.025))
TG_TOKEN = os.getenv("TELEGRAM_TOKEN")
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID")
GROQ_KEY = os.getenv("GROQ_API_KEY")

def fetch_data():
    try:
        v = yf.Ticker(VWCE).history(period="6mo")["Close"]
        i = yf.Ticker(IBTM).history(period="6mo")["Close"]
        common = v.index.intersection(i.index)
        return v[common], i[common]
    except Exception as e:
        return None, None

def calc_metrics(v, i):
    port = (v * H_VWCE) + (i * H_IBTM)
    if len(port) < 10: return None
    
    cur = port.iloc[-1]
    days = (port.index[-1] - port.index[0]).days or 1
    ret = (cur / CAPITAL) - 1
    cagr = (1 + ret) ** (365/days) - 1
    real_cagr = (1 + cagr) / (1 + INFLATION) - 1
    
    daily_ret = port.pct_change().dropna()
    vol = daily_ret.std() * np.sqrt(252)
    
    peak = port.expanding().max()
    max_dd = ((port - peak) / peak).min()
    
    sharpe = (cagr - 0.03) / vol if vol > 0 else 0
    
    return {
        "val": round(cur, 2), "ret": round(ret*100, 2),
        "cagr": round(real_cagr*100, 2), "vol": round(vol*100, 2),
        "dd": round(max_dd*100, 2), "sharpe": round(sharpe, 2),
        "days": days
    }

def ai_report(m):
    prompt = f"""Sei un analista finanziario socratico per uno studente di economia.
Dati: Valore {m['val']}€ | Rend.Reale {m['cagr']}% | Vol {m['vol']}% | MaxDD {m['dd']}% | Sharpe {m['sharpe']} | Giorni {m['days']}
Genera un report di 3 righe: 1) Sintesi stato 2) Valutazione rischio 3) Una domanda socratica per lo studio. Max 120 parole."""
    try:
        res = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
            json={"model": "llama-3.1-8b-instant", "messages": [{"role": "user", "content": prompt}], "max_tokens": 250, "temperature": 0.3}
        )
        return res.json()["choices"][0]["message"]["content"]
    except:
        return "⚠️ AI offline. Verifica metriche manualmente."

def send(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                      json={"chat_id": TG_CHAT, "text": msg, "parse_mode": "Markdown"})
    except: pass

def main():
    v, i = fetch_data()
    if v is None:
        send("❌ Errore download dati di mercato.")
        return
        
    m = calc_metrics(v, i)
    if not m:
        send("⏳ Dati insufficienti per l'analisi (serve più storico).")
        return
        
    ai_text = ai_report(m)
    msg = f"📊 *Report Portafoglio - {datetime.date.today()}*\n\n"
    msg += f"💰 Valore: *{m['val']}€*\n"
    msg += f"📈 Rend.Reale: *{m['cagr']}%* | Vol: *{m['vol']}%*\n"
    msg += f"📉 Max Drawdown: *{m['dd']}%* | Sharpe: *{m['sharpe']}*\n\n"
    msg += f"🤖 *Analisi AI:*\n{ai_text}"
    send(msg)
    print("✅ Inviato")

if __name__ == "__main__":
    main()
