import os, yfinance as yf, requests, numpy as np, datetime, math

# TEMPORANEO - SOLO PER TEST!
H_VWCE = 4000.0
H_IBTM = 1000.0
CAPITAL = 5000.0
INFLATION = 0.025
TG_TOKEN = "8876010394:AAHK3wjlNm2DQfPDt1pgkPM73bTBjXmZa3A"
TG_CHAT = "1103185363"
GROQ_KEY = "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"

# Commenta le righe originali:
# H_VWCE = float(os.getenv("HOLDINGS_VWCE", 35.0))
# H_IBTM = float(os.getenv("HOLDINGS_IBTM", 8.0))
# CAPITAL = float(os.getenv("INITIAL_CAPITAL", 5000.0))
# INFLATION = float(os.getenv("INFLATION_RATE", 0.025))
# TG_TOKEN = os.getenv("TELEGRAM_TOKEN")
# TG_CHAT = os.getenv("TELEGRAM_CHAT_ID")
# GROQ_KEY = os.getenv("GROQ_API_KEY")

def main():
    v, i = fetch_data()
    if v is None:
        send("❌ Errore download dati di mercato.")
        return
        
    m = calc_metrics(v, i)
    if not m:
        send("⏳ Dati insufficienti per l'analisi (serve più storico).")
        return
    
    # DEBUG: stampa cosa sta succedendo
    print(f"DEBUG: Valore portafoglio = {m['val']}")
    print(f"DEBUG: Chiamata AI in corso...")
    
    ai_text = ai_report(m)
    print(f"DEBUG: Risposta AI ricevuta: {ai_text[:50]}...")  # prime 50 chars
    
    msg = f"📊 *Report Portafoglio - {datetime.date.today()}*\n\n"
    msg += f"💰 Valore: *{m['val']}€*\n"
    msg += f"📈 Rend.Reale: *{m['cagr']}%* | Vol: *{m['vol']}%*\n"
    msg += f"📉 Max Drawdown: *{m['dd']}%* | Sharpe: *{m['sharpe']}*\n\n"
    msg += f"🤖 *Analisi AI:*\n{ai_text}"
    
    print(f"DEBUG: Messaggio finale:\n{msg}")
    send(msg)
    print("✅ Inviato")

if __name__ == "__main__":
    print("DEBUG: Avvio bot con valori hardcoded")
    main()
