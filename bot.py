
import os
import requests
from datetime import datetime, timezone

# صياد السيولة - النسخة الأولى

ALPACA_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET = os.getenv("ALPACA_SECRET_KEY")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID")

SYMBOLS = os.getenv(
    "STOCK_SYMBOLS",
    "AAPL,TSLA,NVDA,AMD,PLTR,SOFI,MARA,RIOT,INTC,AMZN"
).split(",")

BASE = "https://data.alpaca.markets/v2"

HEADERS = {
    "APCA-API-KEY-ID": ALPACA_KEY or "",
    "APCA-API-SECRET-KEY": ALPACA_SECRET or ""
}


def get_bars(symbol, timeframe, limit):
    url = f"{BASE}/stocks/{symbol}/bars"
    params = {
        "timeframe": timeframe,
        "limit": limit,
        "feed": "iex"
    }

    response = requests.get(
        url, headers=HEADERS, params=params, timeout=20
    )
    response.raise_for_status()
    return response.json().get("bars", [])


def analyze(symbol):
    minute_bars = get_bars(symbol, "1Min", 5)
    daily_bars = get_bars(symbol, "1Day", 21)

    if len(minute_bars) < 5 or len(daily_bars) < 10:
        return None

    volume_now = sum(b["v"] for b in minute_bars)
    avg_daily_volume = sum(
        b["v"] for b in daily_bars[:-1]
    ) / len(daily_bars[:-1])

    expected_volume = avg_daily_volume * 5 / 390

    if expected_volume <= 0:
        return None

    relative_volume = volume_now / expected_volume

    buy_volume = sum(
        b["v"] for b in minute_bars if b["c"] >= b["o"]
    )
    sell_volume = volume_now - buy_volume

    buy_pressure = buy_volume / max(volume_now, 1) * 100
    net_pressure = buy_pressure - (
        sell_volume / max(volume_now, 1) * 100
    )

    price = minute_bars[-1]["c"]

    return {
        "symbol": symbol,
        "price": price,
        "volume": volume_now,
        "relative": relative_volume,
        "buy": buy_pressure,
        "net": net_pressure
    }


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"

    response = requests.post(
        url,
        json={
            "chat_id": TG_CHAT,
            "text": message
        },
        timeout=20
    )
    response.raise_for_status()


def main():
    if not all([ALPACA_KEY, ALPACA_SECRET, TG_TOKEN, TG_CHAT]):
        raise RuntimeError("Missing required configuration secrets")

    results = []

    for symbol in SYMBOLS:
        try:
            result = analyze(symbol.strip().upper())
            if result:
                results.append(result)
        except Exception as error:
            print(f"{symbol}: {error}")

    results.sort(
        key=lambda x: x["relative"] * max(x["net"], 0),
        reverse=True
    )

    message = "🎯 صياد السيولة\n"
    message += "📊 تقرير مراقبة الأسهم الأمريكية\n\n"

    for item in results[:10]:
        message += (
            f"🔹 {item['symbol']}\n"
            f"السعر: ${item['price']:.2f}\n"
            f"الحجم النسبي: {item['relative']:.2f}x\n"
            f"ضغط الشراء التقديري: {item['buy']:.1f}%\n"
            f"صافي الضغط التقديري: {item['net']:.1f}%\n\n"
        )

    if not results:
        message += "لا توجد بيانات كافية حالياً."

    message += "\n⚠️ ضغط الشراء تقديري وليس تدفق أوامر حقيقياً."
    message += "\n🕒 " + datetime.now(timezone.utc).strftime("%H:%M UTC")

    send_telegram(message)


if __name__ == "__main__":
    main()
