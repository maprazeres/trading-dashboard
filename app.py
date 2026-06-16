import requests
import time
import datetime
from pybit.unified_trading import HTTP
from dotenv import load_dotenv
import os as system_os
import sys

sys.stdout.reconfigure(encoding='utf-8')

# CONFIG
load_dotenv()

api_key = system_os.getenv("API_KEY")
api_secret = system_os.getenv("API_SECRET")

session = HTTP(testnet=False, api_key=api_key, api_secret=api_secret)

# =========================
# MARKET FUNCTIONS
# =========================
def get_all_symbols():
    try:
        url = "https://api.bybit.com/v5/market/tickers?category=linear"
        return requests.get(url, timeout=10).json()['result']['list']
    except Exception as e:
        print(f"Erro get_all_symbols: {e}", flush=True)
        return []

def get_klines(symbol, limit=50):
    try:
        url = f"https://api.bybit.com/v5/market/kline?category=linear&symbol={symbol}&interval=240&limit={limit}"
        data = requests.get(url, timeout=10).json()
        return data.get('result', {}).get('list', [])
    except Exception as e:
        print(f"Erro get_klines {symbol}: {e}", flush=True)
        return []

# =========================
# INDICADORES
# =========================
def get_indicators(symbol):
    candles = get_klines(symbol)

    if len(candles) < 30:
        return None

    closes = [float(c[4]) for c in candles]
    volumes = [float(c[5]) for c in candles]

    sma8 = sum(closes[:8]) / 8
    sma21 = sum(closes[:21]) / 21

    prev_sma8 = sum(closes[1:9]) / 8
    prev_sma21 = sum(closes[1:22]) / 21

    trend_up = sma8 > sma21
    trend_down = sma8 < sma21

    crossover_up = prev_sma8 < prev_sma21 and sma8 > sma21
    crossover_down = prev_sma8 > prev_sma21 and sma8 < sma21

    # RSI
    gains = []
    losses = []

    for i in range(1, 15):
        diff = closes[i-1] - closes[i]
        if diff > 0:
            gains.append(diff)
        else:
            losses.append(abs(diff))

    avg_gain = sum(gains) / (len(gains) or 1)
    avg_loss = sum(losses) / (len(losses) or 1)

    rs = avg_gain / (avg_loss if avg_loss != 0 else 1)
    rsi = 100 - (100 / (1 + rs))

    volume_now = volumes[0]
    volume_prev = volumes[1]

    price_now = closes[0]
    price_prev = closes[1]

    volume_up = volume_now > volume_prev
    volume_long = volume_now > volume_prev and price_now > price_prev
    volume_short = volume_now > volume_prev and price_now < price_prev

    supertrend_up = closes[0] > sum(closes[:10]) / 10
    supertrend_down = not supertrend_up

    return {
        "trend_up": trend_up,
        "trend_down": trend_down,
        "crossover_up": crossover_up,
        "crossover_down": crossover_down,
        "rsi": rsi,
        "volume_up": volume_up,
        "volume_long": volume_long,
        "volume_short": volume_short,
        "supertrend_up": supertrend_up,
        "supertrend_down": supertrend_down
    }

# =========================
# ANÁLISE INDIVIDUAL
# =========================
def analyze_symbol(symbol, symbols_data):
    """Análise detalhada de um símbolo individual"""
    try:
        btc_change = 0
        for coin in symbols_data:
            if coin.get('symbol') == "BTCUSDT":
                btc_change = float(coin.get('price24hPcnt', 0)) * 100
                break

        coin_data = next((c for c in symbols_data if c.get('symbol') == symbol), None)

        if not coin_data:
            return {"error": f"Símbolo {symbol} não encontrado"}

        change = float(coin_data.get('price24hPcnt', 0)) * 100
        price = float(coin_data.get('lastPrice', 0))
        volume = float(coin_data.get('turnover24h', 0))

        strength = change - btc_change

        # FILTROS BÁSICOS
        if price < 0.01:
            return {"error": "❌ Preço muito baixo (< $0.01)"}
        
        if volume < 10_000_000:
            return {"error": f"❌ Volume insuficiente (${volume:,.0f} < $10M)"}

        indicators = get_indicators(symbol)

        if not indicators:
            return {"error": "❌ Sem dados suficientes de candles"}

        score = 0

        # SCORING
        if indicators["trend_up"] or indicators["trend_down"]:
            score += 1
        if indicators["crossover_up"] or indicators["crossover_down"]:
            score += 1
        if indicators["supertrend_up"] or indicators["supertrend_down"]:
            score += 1
        if 40 <= indicators["rsi"] <= 65:
            score += 1
        if indicators["volume_up"]:
            score += 1

        direction = "NEUTRO"

        if indicators["trend_up"] and indicators["supertrend_up"] and strength > 0:
            direction = "LONG"
        elif indicators["trend_down"] and indicators["supertrend_down"] and strength < 0:
            direction = "SHORT"

        entry = "AGUARDAR"

        if indicators["crossover_up"] and indicators["volume_long"] and direction == "LONG":
            entry = "🔥 LONG ENTRY"
        elif indicators["crossover_down"] and indicators["volume_short"] and direction == "SHORT":
            entry = "🔻 SHORT ENTRY"

        return {
            "symbol": symbol,
            "score": score,
            "direction": direction,
            "entry": entry,
            "strength": strength,
            "change": change,
            "price": price,
            "volume": volume,
            "indicators": {
                "trend": "UP" if indicators["trend_up"] else ("DOWN" if indicators["trend_down"] else "NONE"),
                "crossover": "UP" if indicators["crossover_up"] else ("DOWN" if indicators["crossover_down"] else "NONE"),
                "rsi": f"{indicators['rsi']:.1f}",
                "supertrend": "UP" if indicators["supertrend_up"] else "DOWN",
                "volume_trend": "UP" if indicators["volume_up"] else "DOWN"
            }
        }
    except Exception as e:
        return {"error": f"Erro ao analisar {symbol}: {str(e)}"}

def analyze_user_input():
    """Interface interativa para análise individual de símbolos"""
    print("\n" + "="*50, flush=True)
    print("🔍 ANÁLISE INDIVIDUAL DE MOEDAS", flush=True)
    print("="*50, flush=True)
    
    symbols_data = get_all_symbols()
    if not symbols_data:
        print("❌ Erro ao carregar dados da API", flush=True)
        return
    
    while True:
        try:
            symbol = input("\n📍 Digite a moeda (ex: BTCUSDT) ou 'sair': ").strip().upper()
            
            if symbol == "SAIR":
                break
            
            if not symbol or len(symbol) < 3:
                print("❌ Símbolo inválido", flush=True)
                continue
            
            print("\n⏳ Analisando...\n", flush=True)
            result = analyze_symbol(symbol, symbols_data)
            
            if "error" in result:
                print(f"⚠️  {result['error']}", flush=True)
            else:
                print(f"📊 ANÁLISE: {result['symbol']}", flush=True)
                print(f"   Preço: ${result['price']:.6f}", flush=True)
                print(f"   Volume 24h: ${result['volume']:,.0f}", flush=True)
                print(f"   Mudança 24h: {result['change']:.2f}%", flush=True)
                print(f"   Força vs BTC: {result['strength']:.2f}%", flush=True)
                print(f"\n   Direção: {result['direction']}", flush=True)
                print(f"   Score: {result['score']}/5", flush=True)
                print(f"   Entry: {result['entry']}", flush=True)
                print(f"\n   Indicadores:", flush=True)
                print(f"   - Trend: {result['indicators']['trend']}", flush=True)
                print(f"   - Crossover: {result['indicators']['crossover']}", flush=True)
                print(f"   - RSI: {result['indicators']['rsi']}", flush=True)
                print(f"   - Supertrend: {result['indicators']['supertrend']}", flush=True)
                print(f"   - Volume: {result['indicators']['volume_trend']}", flush=True)
                
                if result['score'] >= 3:
                    print(f"\n✅ IR PARA GRÁFICO E CONFIRMAR!", flush=True)
                else:
                    print(f"\n⚠️  Score baixo, revisar outros sinais", flush=True)
        
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"❌ Erro: {e}", flush=True)

# =========================
# MODO DE EXECUÇÃO
# =========================
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "analyze":
        # Modo análise individual
        analyze_user_input()
    else:
        # Modo loop contínuo (padrão)
        print("\n🚀 Iniciando em modo LOOP CONTÍNUO", flush=True)
        print("   Para modo análise individual: python app.py analyze", flush=True)
        print()
        
        while True:
            modo = input("\n📍 Digite 1 para scanner ou símbolo (ex: BTCUSDT): ").upper()
            
            symbols_data = get_all_symbols()

            if modo != "1":
                resultado = analyze_symbol(modo, symbols_data)

                print("\n🔍 ANÁLISE INDIVIDUAL:\n")

                if not resultado:
                    print("Moeda não encontrada")
                elif "error" in resultado:
                    print(resultado["error"])
                else:
                    print(f"Moeda: {resultado['symbol']}")
                    print(f"Score: {resultado['score']}")
                    print(f"Direção: {resultado['direction']}")
                    print(f"Entrada: {resultado['entry']}")
                    print(f"Força: {resultado['strength']:.2f}%")

                input("\nPressione ENTER para continuar...")
                continue
            
            # Modo scanner (1)
            try:
                inicio = datetime.datetime.now()

                print("\n===== SCANNER INICIADO =====", flush=True)
                print(f"{inicio.strftime('%d/%m %H:%M:%S')}", flush=True)

                if not symbols_data:
                    print("Erro ao carregar mercado", flush=True)
                    time.sleep(10)
                    continue

                btc_change = 0
                for coin in symbols_data:
                    if coin['symbol'] == "BTCUSDT":
                        btc_change = float(coin['price24hPcnt']) * 100
                        break

                ranking = []

                for coin in symbols_data[:30]:
                    try:
                        symbol = coin['symbol']

                        if symbol == "BTCUSDT":
                            continue

                        change = float(coin['price24hPcnt']) * 100
                        price = float(coin['lastPrice'])
                        volume = float(coin['turnover24h'])

                        strength = change - btc_change

                        if price < 0.01:
                            continue

                        if volume < 10_000_000:
                            continue

                        if not (2 <= abs(strength) <= 15):
                            continue

                        indicators = get_indicators(symbol)

                        if not indicators:
                            continue

                        score = 0
                        if indicators["trend_up"] or indicators["trend_down"]:
                            score += 1
                        if indicators["crossover_up"] or indicators["crossover_down"]:
                            score += 1
                        if indicators["supertrend_up"] or indicators["supertrend_down"]:
                            score += 1
                        if 40 <= indicators["rsi"] <= 65:
                            score += 1
                        if indicators["volume_up"]:
                            score += 1

                        direction = "NEUTRO"
                        if indicators["trend_up"] and indicators["supertrend_up"] and strength > 0:
                            direction = "LONG"
                        elif indicators["trend_down"] and indicators["supertrend_down"] and strength < 0:
                            direction = "SHORT"

                        entry = "AGUARDAR"
                        if indicators["crossover_up"] and indicators["volume_long"] and direction == "LONG":
                            entry = "🔥 LONG ENTRY"
                        elif indicators["crossover_down"] and indicators["volume_short"] and direction == "SHORT":
                            entry = "🔻 SHORT ENTRY"

                        ranking.append({
                            "symbol": symbol,
                            "score": score,
                            "direction": direction,
                            "entry": entry
                        })

                    except Exception as e:
                        print(f"Erro {symbol}: {e}", flush=True)

                print("\nTOP OPORTUNIDADES:\n", flush=True)

                for coin in ranking[:10]:
                    print(f"{coin['symbol']} | {coin['direction']} | {coin['entry']} | Score: {coin['score']}", flush=True)

                print("\nAguardando 60s...\n", flush=True)
                
                # ================= POSIÇÕES =================
                print("\n💼 SUAS POSIÇÕES:\n", flush=True)

                try:
                    response = session.get_positions(
                        category="linear",
                        settleCoin="USDT"
                    )

                    positions = response['result']['list']

                    total_pnl = 0

                    for pos in positions:
                        size = float(pos['size'])

                        if size == 0:
                            continue

                        symbol = pos['symbol']
                        side = pos['side']
                        pnl = float(pos['unrealisedPnl'])

                        total_pnl += pnl

                        tipo = "LONG 🟢" if side == "Buy" else "SHORT 🔴"

                        print(f"{symbol} | {tipo} | PnL: ${pnl:.2f}", flush=True)

                    print("\n📊 RESUMO:", flush=True)
                    print(f"PnL TOTAL: ${total_pnl:.2f}", flush=True)

                except Exception as e:
                    print(f"Erro ao carregar posições: {e}", flush=True)

                input("\n⏱️ Pressione ENTER para nova análise ou Ctrl+C para sair...")

            except Exception as e:
                print(f"ERRO GERAL: {e}", flush=True)
                time.sleep(10)
