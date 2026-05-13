import os, yfinance as yf, requests, numpy as np, datetime, math

# TEMPORANEO - SOLO PER TEST! (rimuovi dopo aver verificato)
H_VWCE = 4000.0
H_IBTM = 1000.0
CAPITAL = 5000.0
INFLATION = 0.025
TG_TOKEN = "8876010394:AAHK3wjlNm2DQfPDt1pgkPM73bTBjXmZa3A"
TG_CHAT = "1103185363"
GROQ_KEY = "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"

def fetch_data():
    try:
        # Prova con i ticker globali (più affidabili)
        v = yf.Ticker("VWCE.DE").history(period="6mo")["Close"]   # Xetra invece di Milano
        i = yf.Ticker("IB01.L").history(period="6mo")["Close"]    # Londra invece di Milano
        
        # Se non funzionano, prova questi fallback:
        if len(v) < 10:
            v = yf.Ticker("IWDA.AS").history(period="6mo")["Close"]  # iShares Core MSCI World (Amsterdam)
        if len(i) < 10:
            i = yf.Ticker("AGGH.L").history(period="6mo")["Close"]   # iShares Global Govt Bond (Londra)
        
        common = v.index.intersection(i.index)
        if len(common) < 10:
            print(f"Errore: solo {len(common)} giorni di dati comuni")
            return None, None
            
        return v[common], i[common]
    except Exception as e:
        print(f"Errore download dati: {e}")
        return None, None

def calc_metrics(v, i):
    port = (v * H_VWCE) + (i * H_IBTM)
    if len(port) < 10: 
        print("Dati insufficienti")
        return None
    
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
    except Exception as e:
        print(f"Errore AI: {e}")
        return "⚠️ AI offline. Verifica metriche manualmente."

def send(msg):
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        payload = {"chat_id": TG_CHAT, "text": msg, "parse_mode": "Markdown"}
        r = requests.post(url, json=payload)
        print(f"Telegram response: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"Errore Telegram: {e}")

def main():
    print("DEBUG: Avvio bot con valori hardcoded")
    v, i = fetch_data()
    if v is None:
        send("❌ Errore download dati di mercato.")
        return
        
    m = calc_metrics(v, i)
    if not m:
        send("⏳ Dati insufficienti per l'analisi (serve più storico).")
        return
        
    print(f"DEBUG: Valore portafoglio = {m['val']}")
    print(f"DEBUG: Chiamata AI in corso...")
    
    ai_text = ai_report(m)
    print(f"DEBUG: Risposta AI ricevuta: {ai_text[:50]}...")
    
    msg = f"📊 *Report Portafoglio - {datetime.date.today()}*\n\n"
    msg += f"💰 Valore: *{m['val']}€*\n"
    msg += f"📈 Rend.Reale: *{m['cagr']}%* | Vol: *{m['vol']}%*\n"
    msg += f"📉 Max Drawdown: *{m['dd']}%* | Sharpe: *{m['sharpe']}*\n\n"
    msg += f"🤖 *Analisi AI:*\n{ai_text}"
    
    print(f"DEBUG: Messaggio finale:\n{msg}")
    send(msg)
    print("✅ Inviato")

if __name__ == "__main__":
    main()
