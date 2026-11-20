
import requests
from datetime import datetime, time
from zoneinfo import ZoneInfo

# ==================================
# صيّاد السيولة - تحليل ضغط الشراء والبيع
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
    highs = quotes.get("high", [])
    lows = quotes.get("low", [])

    today_volume = 0
    last_price = None

    buy_flow = 0
    sell_flow = 0

    for stamp, volume, close, high, low in zip(
        timestamps, volumes, closes, highs, lows
    ):
        if volume is None or close is None:
            continue

        candle_time = datetime.fromtimestamp(stamp, NY)

        if candle_time.date() != today:
            continue

        if not (time(9, 30) <= candle_time.time() <= time(16, 0)):
            continue

        today_volume += volume
        last_price = close

        if volume <= 0:
            continue

        # تقدير ضغط الشراء والبيع من موقع الإغلاق
        price_range = high - low if high is not None and low is not None else 0

        if price_range > 0:
            buy_ratio = (close - low) / price_range
            buy_ratio = max(0, min(1, buy_ratio))
        else:
            buy_ratio = 0.5

        sell_ratio = 1 - buy_ratio

        traded_value = volume * close

        buy_flow += traded_value * buy_ratio
        sell_flow += traded_value * sell_ratio

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

    net_flow = buy_flow - sell_flow

    total_flow = buy_flow + sell_flow

    buy_percent = (
        buy_flow / total_flow * 100
        if total_flow > 0 else 0
    )

    return {
        "symbol": symbol,
        "price": last_price,
        "volume": today_volume,
        "relative": relative_volume,
        "buy_flow": buy_flow,
        "sell_flow": sell_flow,
        "net_flow": net_flow,
        "buy_percent": buy_percent
    }


def main():
    print("=" * 50)
    print("          صيّاد السيولة")
    print("   مراقبة الأسهم الأمريكية")
    print("=" * 50)

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
        return

    for item in results[:10]:
        print(
            f"\nالسهم: {item['symbol']}"
            f"\nالسعر: ${item['price']:.2f}"
            f"\nالحجم: {item['volume']:,.0f}"
            f"\nالنشاط النسبي: {item['relative']:.2f}x"
            f"\nالسيولة الشرائية التقديرية: ${item['buy_flow']:,.0f}"
            f"\nالسيولة البيعية التقديرية: ${item['sell_flow']:,.0f}"
            f"\nصافي السيولة التقديري: ${item['net_flow']:,.0f}"
            f"\nنسبة ضغط الشراء: {item['buy_percent']:.1f}%"
        )
        print("-" * 40)

    print("\nانتهى الفحص.")
    print("مصدر البيانات: Yahoo Finance")
    print("تنبيه: السيولة المعروضة تقديرية وليست تدفقات فعلية.")


if __name__ == "__main__":
    main()
