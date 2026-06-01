# Free Price Alert Bot (WhatsApp + GitHub Actions)

Monitors stocks and metals (gold, silver, etc.) and sends a **WhatsApp message** when any price drops below your threshold. Runs entirely on **GitHub Actions** — no server, no API keys to pay for, $0/month.

## What you get

- WhatsApp alerts via **CallMeBot** (free, legal, opt-in)
- Optional Telegram alerts as a backup channel
- Price data from Yahoo Finance (no API key needed)
- Cooldown logic so you don't get spammed if a price stays low
- Auto-clears state when price recovers, so future drops re-alert you

## Setup (~10 minutes)

### 1. Authorize CallMeBot on WhatsApp

This is the part that makes WhatsApp delivery free and policy-compliant — you give explicit consent for the bot to message you.

1. Save this phone number in your contacts as `CallMeBot`: **+34 644 51 95 23**
2. Open WhatsApp, message that contact with **exactly** this text:
   ```
   I allow callmebot to send me messages
   ```
3. Wait up to 2 minutes. You'll get a reply containing your API key (e.g., `Your APIKEY is: 1234567`). Save it.

### 2. Create a GitHub repo

1. Create a new GitHub repo (private is fine).
2. Upload these files (drag-and-drop in the GitHub UI works):
   - `price_alert.py`
   - `config.yaml`
   - `requirements.txt`
   - `.github/workflows/check_prices.yml`

### 3. Add secrets

In your repo: **Settings → Secrets and variables → Actions → New repository secret**

| Name | Value |
|------|-------|
| `WHATSAPP_PHONE` | Your number with country code, no `+` or spaces (e.g. `14085551234`) |
| `WHATSAPP_APIKEY` | The key CallMeBot sent you |

### 4. Edit `config.yaml`

Set the assets you care about and the price levels at which you want alerts. Example tickers are in the file comments.

### 5. Test it

Go to the **Actions** tab in your repo → click `Price Alert Check` → `Run workflow`. Within ~30 seconds you'll see the run complete. If any price is below threshold, you'll get a WhatsApp message.

> **Tip for testing:** temporarily set a `drop_below` value very high (e.g., gold below `$10,000`) so an alert *definitely* fires. Then change it back.

## Adjusting frequency

Edit the `cron:` line in `.github/workflows/check_prices.yml`:

| Cron | Meaning |
|------|---------|
| `*/30 * * * 1-5` | Every 30 min, weekdays (default) |
| `0 * * * *` | Every hour, 24/7 |
| `*/15 13-21 * * 1-5` | Every 15 min during US market hours |
| `0 */4 * * *` | Every 4 hours |

GitHub Actions cron is in **UTC**.

## Cost & limits

- **GitHub Actions**: 2,000 free minutes/month for private repos, unlimited for public. The default schedule uses ~120 min/month — well within the free tier.
- **CallMeBot**: Free for personal use. Don't blast hundreds of messages in a row or they'll throttle.
- **Yahoo Finance**: Free, no key. Be polite — don't lower the cron to every minute.

## Optional: add Telegram as a backup

Telegram is the most reliable free messaging API. Useful if CallMeBot is ever down.

1. Open Telegram, message `@BotFather`, send `/newbot`, follow prompts, save the token.
2. Message your new bot once (so it can message you back).
3. Visit `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` and find your `chat.id`.
4. Add two more secrets to GitHub: `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.

The script will send to both channels if both are configured.

## Troubleshooting

- **No WhatsApp message arrived?** Open the failed Actions run → check the log. CallMeBot's response is printed if it failed.
- **CallMeBot never replied to your "I allow" message?** They sometimes take up to 2 min. If still nothing, try again from a different phone or contact their support.
- **Workflow not running on schedule?** GitHub pauses scheduled workflows on inactive repos (~60 days). Push any commit to wake it back up.
