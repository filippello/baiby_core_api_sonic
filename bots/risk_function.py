import requests
import pandas as pd
import numpy as np
from web3 import Web3
from eth_abi import decode


def decode_data(calldata):

    try:
        # Extraemos el selector de función (primeros 4 bytes)
        function_selector = calldata[:8]
        print(f"Selector de función: 0x{function_selector}")
        recipient_address = "0x" + calldata[-452:-412]  # Indices correctos en orden

        print(f"recipient_address: {recipient_address}")
    except Exception as e:
        print(f"Error al decodificar: {str(e)}")
    return [function_selector,recipient_address]


def get_token_id_from_address(recipient_address, platform="arbitrum-one"):
    url = f"https://api.coingecko.com/api/v3/coins/{platform}/contract/{recipient_address}"
    response = requests.get(url)
    #print(response.json())
    if response.status_code == 200:
        data = response.json()
        return data["id"]  # Devuelve el token_id
    else:
        print(f"Error {response.status_code}: {response.text}")
        return None

def get_market_data(token_id="pepe", vs_currency="usd", days=30):
    """
    Obtiene datos de mercado (precios, market cap y volumen) de la API de CoinGecko.
    """
    url = f"https://api.coingecko.com/api/v3/coins/{token_id}/market_chart"
    params = {
        "vs_currency": vs_currency,
        "days": days,
        "interval": "daily"
    }
    response = requests.get(url, params=params)
    if response.status_code != 200:
        raise Exception(f"Error al obtener datos: {response.status_code}")
    return response.json()

def process_data(data):
    """
    Procesa los datos históricos de precios y calcula los retornos diarios.
    """
    prices = data["prices"]
    df = pd.DataFrame(prices, columns=["timestamp", "price"])
    # Convertir el timestamp de milisegundos a datetime
    df["date"] = pd.to_datetime(df["timestamp"], unit='ms')
    df = df.set_index("date").sort_index()
    # Calcular los retornos diarios (porcentaje de cambio)
    df["returns"] = df["price"].pct_change()
    # Se elimina el primer valor NaN resultante del cálculo
    df = df.dropna()
    return df

def calculate_volatility(df):
    """
    Calcula la volatilidad diaria y la anualizada (asumiendo 252 días de negociación al año).
    """
    daily_vol = df["returns"].std()
    annual_vol = daily_vol * np.sqrt(252)
    return daily_vol, annual_vol

def assess_risk(annual_vol):
    """
    Evalúa el riesgo del token basado en la volatilidad anual.
    
    Esta función es un ejemplo simplificado:
      - Volatilidad anual >= 1.0 -> riesgo Alto
      - 0.5 <= Volatilidad anual < 1.0 -> riesgo Medio
      - Volatilidad anual < 0.5 -> riesgo Bajo
    """
    if annual_vol >= 1.0:
        return "High"
    elif annual_vol >= 0.5:
        return "Medium"
    else:
        return None

def calculate_risk(calldata):

    #calldata = "3593564c000000000000000000000000000000000000000000000000000000000000006000000000000000000000000000000000000000000000000000000000000000a00000000000000000000000000000000000000000000000000000000067aea11c00000000000000000000000000000000000000000000000000000000000000040b000604000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000008000000000000000000000000000000000000000000000000000000000000000e000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000000280000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000de0b6b3a7640000000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000de0b6b3a7640000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000a00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000002b0d500b1d8e8ef31e21c99d1db9a6444d3adf12700001f43c499c542cef5e3811e1192ce70d8cc03d5c3359"
    risk_level  = None

    function_selector,recipient_address = decode_data(calldata)
    print(function_selector,recipient_address)
    if function_selector == "8d80ff0a":
        token = get_token_id_from_address(recipient_address)
        #token = "pepe"  # Cambia por el token deseado, por ejemplo "ethereum"
        try:
            data = get_market_data(token, days=30)
        except Exception as e:
            print(e)
            return

        # Procesar datos y calcular volatilidad
        df = process_data(data)
        daily_vol, annual_vol = calculate_volatility(df)

        # Obtener la última capitalización de mercado y volumen de trading (como proxies de liquidez)
        market_caps = data.get("market_caps", [])
        volumes = data.get("total_volumes", [])
        latest_market_cap = market_caps[-1][1] if market_caps else None
        latest_volume = volumes[-1][1] if volumes else None

        # Mostrar resultados
        print(f"Token: {token}")
        print(f"Volatilidad diaria: {daily_vol:.4f}")
        print(f"Volatilidad anualizada: {annual_vol:.4f}")
        print(f"Capitalización de mercado reciente: {latest_market_cap}")
        print(f"Volumen de trading reciente: {latest_volume}")

        # Evaluar el riesgo basado en la volatilidad anual
        risk_level = assess_risk(annual_vol)
        print(f"Nivel de riesgo estimado: {risk_level}")

    else:
        print("No es un swap de token")
        token_id = None

    return risk_level
