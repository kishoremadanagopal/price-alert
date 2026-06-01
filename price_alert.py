"""
Price Alert Bot
Checks prices for stocks/metals and sends WhatsApp alerts when thresholds are breached.
Runs on GitHub Actions on a schedule. All data from Yahoo Finance (free, no API key).
"""

import os
import sys
import json
import yaml
import requests
import yfinance as yf
from datetime import datetime, timezone
from pathlib import Path

STATE_FILE = Path("alert_state.json")
COOLDOWN_HOURS = 6  # Avoid re-sending the same alert within this window


def load_config():
    with open("config.yaml", "r") as f:
        return yaml.safe_load(f)


def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            return {}
    return {}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def get_price(ticker):
    """Fetch current price from Yahoo Finance."""
    try:
        t = yf.Ticker(ticker)
        # Try fast_info first (cheaper call)
        try:
            price = t.fast_info["last_price"]
            if price and price > 0:
                return float(price)
        except (KeyError, AttributeError, TypeError):
            pass
        # Fall back to history
        hist = t.history(period="1d")
        if hist.empty:
            return None
        return float(hist["Close"].iloc[-1])
    except Exception as e:
        print(f"  Error fetching {ticker}: {e}", file=sys.stderr)
        return None


def send_whatsapp(phone, apikey, message):
    """Send WhatsApp message via CallMeBot."""
    url = "https://api.callmebot.com/whatsapp.php"
    params = {"phone": phone, "text": message, "apikey": apikey}
    try:
        r = requests.get(url, params=params, timeout=30)
        ok = r.status_code == 200 and "queued" in r.text.lower() or r.status_code == 200
        if not ok:
            print(f"  CallMeBot response: {r.status_code} - {r.text[:200]}", file=sys.stderr)
        return ok
    except Exception as e:
        print(f"  WhatsApp send error: {e}", file=sys.stderr)
        return False


def send_telegram(bot_token, chat_id, message):
    """Send Telegram message (optional fallback channel)."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {"chat_id": chat_id, "text": message}
    try:
        r = requests.post(url, data=data, timeout=30)
        return r.status_code == 200
    except Exception as e:
        print(f"  Telegram send error: {e}", file=sys.stderr)
        return False


def should_alert(state, asset_key, cooldown_hours):
    """Avoid alert spam — only alert if cooldown has passed since last alert for this asset."""
    last = state.get(asset_key)
    if not last:
        return True
    last_dt = datetime.fromisoformat(last)
    elapsed = (datetime.now(timezone.utc) - last_dt).total_seconds() / 3600
    return elapsed >= cooldown_hours


def main():
    config = load_config()
    state = load_state()
    cooldown = config.get("cooldown_hours", COOLDOWN_HOURS)
    alerts = []

    print(f"Checking {len(config['assets'])} assets at {datetime.now(timezone.utc).isoformat()}")
    print("-" * 60)

    for asset in config["assets"]:
        name = asset["name"]
        ticker = asset["ticker"]
        threshold = asset["drop_below"]
        asset_key = f"{name}:{ticker}"

        price = get_price(ticker)
        if price is None:
            print(f"  ✗ {name} ({ticker}): could not fetch price")
            continue

        status = "🔻 BELOW" if price < threshold else "✓ above"
        print(f"  {status} {name} ({ticker}): ${price:,.2f}  threshold: ${threshold:,.2f}")

        if price < threshold:
            if should_alert(state, asset_key, cooldown):
                alerts.append(
                    f"🔻 {name} ({ticker}): ${price:,.2f}\n"
                    f"   (below your ${threshold:,.2f} threshold)"
                )
                state[asset_key] = datetime.now(timezone.utc).isoformat()
            else:
                print(f"      (in cooldown — skipping alert)")
        else:
            # Price recovered above threshold — clear so future drops re-alert
            state.pop(asset_key, None)

    print("-" * 60)

    if not alerts:
        print("No new alerts to send.")
        save_state(state)
        return

    message_lines = ["📊 Price Alert"] + [""] + alerts
    message_lines.append("")
    message_lines.append(f"⏰ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    message = "\n".join(message_lines)

    print(f"\nSending {len(alerts)} alert(s)...")
    print(message)
    print()

    sent_any = False

    # WhatsApp via CallMeBot
    wa_phone = os.environ.get("WHATSAPP_PHONE", "").strip()
    wa_key = os.environ.get("WHATSAPP_APIKEY", "").strip()
    if wa_phone and wa_key:
        if send_whatsapp(wa_phone, wa_key, message):
            print("✓ WhatsApp alert sent.")
            sent_any = True
        else:
            print("✗ WhatsApp send failed.")
    else:
        print("⚠ WhatsApp credentials not set — skipping.")

    # Telegram (optional)
    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    tg_chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if tg_token and tg_chat:
        if send_telegram(tg_token, tg_chat, message):
            print("✓ Telegram alert sent.")
            sent_any = True

    if sent_any:
        save_state(state)
    else:
        print("⚠ No channel succeeded — state not updated so we'll retry next run.")
        sys.exit(1)


if __name__ == "__main__":
    main()
