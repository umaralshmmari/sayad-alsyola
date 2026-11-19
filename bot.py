
import requests
from datetime import datetime, time
from zoneinfo import ZoneInfo

# ==================================
# صيّاد السيولة - النسخة التجريبية
# ==================================

SYMBOLS = [
    "AAPL", "TSLA", "NVDA", "AMD", "PLTR",
    "SOFI", "MARA", "RIOT", "INTC", "AMZN",
    "SMCI", "IONQ", "SOUN", "RGTI", "ONDS"
]

BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/"
NY = ZoneInfo("America/New_York")

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def get_data(symbol, interval, period):
    url = BASE_URL + symbol
    params = {
        "interval": interval,
        "range": period,
        "events": "history"
    }

    response = requests.get(
        url,
        params=params,
        headers=HEADERS,
        timeout=20
    )
    response.raise_for_status()

    data = response.json()["chart"]["result"]

    if not data:
        return None

    return data[0]


def analyze(symbol):
    minute_data = get_data(symbol, "1m", "1d")
    daily_data = get_data(symbol, "1d", "1mo")

    if not minute_data or not daily_data:
        return None

    now = datetime.now(NY)
    today = now.date()

    timestamps = minute_data.get("timestamp", [])
    quotes = minute_data["indicators"]["quote"][0]

    volumes = quotes.get("volume", [])
    closes = quotes.get("close", [])

    today_volume = 0
    last_price = None

    for stamp, volume, close in zip(timestamps, volumes, closes):
        if volume is None:
            continue

        candle_time = datetime.fromtimestamp(
            stamp, NY
        )

        if candle_time.date() != today:
            continue

        if not (time(9, 30) <= candle_time.time() <= time(16, 0)):
            continue

        today_volume += volume

        if close is not None:
            last_price = close

    daily_quotes = daily_data["indicators"]["quote"][0]
    daily_volumes = daily_quotes.get("volume", [])

    valid_volumes = [
        v for v in daily_volumes[:-1]
        if v is not None and v > 0
    ][-20:]

    if len(valid_volumes) < 5:
        return None

    average_volume = sum(valid_volumes) / len(valid_volumes)

    market_start = datetime.combine(
        today, time(9, 30), NY
    )

    elapsed = (now - market_start).total_seconds() / 60
    elapsed = max(1, min(elapsed, 390))

    expected_volume = average_volume * elapsed / 390

    if expected_volume <= 0 or last_price is None:
        return None

    relative_volume = today_volume / expected_volume

    return {
        "symbol": symbol,
        "price": last_price,
        "volume": today_volume,
        "average": average_volume,
        "relative": relative_volume
    }


def main():
    print("=" * 40)
    print("       صيّاد السيولة")
    print("   مراقبة الأسهم الأمريكية")
    print("=" * 40)

    results = []

    for symbol in SYMBOLS:
        try:
            result = analyze(symbol)

            if result:
                results.append(result)
                print("تم فحص:", symbol)

        except Exception as error:
            print("تعذر فحص", symbol, "-", error)

    results.sort(
        key=lambda x: x["relative"],
        reverse=True
    )

    print("\n===== أعلى الأسهم نشاطاً =====\n")

    if not results:
        print("لا توجد بيانات كافية حالياً.")
        print("قد يكون السوق مغلقاً أو البيانات غير متاحة.")
        return

    for item in results[:10]:
        print(
            f"{item['symbol']} | "
            f"السعر: ${item['price']:.2f} | "
            f"الحجم: {item['volume']:,.0f} | "
            f"النشاط النسبي: {item['relative']:.2f}x"
        )

    print("\nانتهى الفحص.")
    print("مصدر البيانات: Yahoo Finance")


if __name__ == "__main__":
    main()
