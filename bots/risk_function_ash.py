import re
import logging
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN_MAPPINGS = {
    "ASH-e3d1b7": "ASH-a642d1"  # Mapeo del token ASH
}

def decode_data(data: str):
    """
    Decodifica el data de la transacción para obtener el token identifier
    """
    try:
        if not data.startswith("composeTasks@"):
            return None, None
            
        parts = data.split("@")
        if len(parts) < 2:
            return None, None
            
        # Extraer el token identifier del data
        token_part = parts[1]
        token_hex = token_part[8:42] if len(token_part) >= 42 else None
        
        if not token_hex:
            return None, None
            
        # Convertir hex a string para obtener el token identifier
        try:
            token_bytes = bytes.fromhex(token_hex.replace('00', ''))
            token_identifier = token_bytes.decode('utf-8')
            return token_identifier, token_hex[24:48]  # Retorna token_id y amount_hex
        except:
            return None, None
            
    except Exception as e:
        logger.error(f"Error decoding data: {e}")
        return None, None

def get_token_id_from_identifier(token_identifier, platform="multiversx"):
    """
    Obtiene la información del token desde la API de MultiversX
    """
    try:
        # Verificar si el token necesita ser mapeado
        token_identifier = TOKEN_MAPPINGS.get(token_identifier, token_identifier)
            
        # Para MultiversX, obtener la información del token
        mvx_api_url = f"https://api.multiversx.com/tokens/{token_identifier}"
        response = requests.get(mvx_api_url)
        
        if response.status_code != 200:
            logger.error(f"Error {response.status_code}: {response.text}")
            return None
            
        token_data = response.json()
        
        # Construir un objeto con la información relevante
        token_info = {
            "name": token_data.get("name", "Unknown Token"),
            "symbol": token_data.get("ticker", token_identifier),
            "id": token_identifier,
            "platform": "multiversx"
        }
        
        logger.info(f"Token info obtenida: {token_info}")
        return token_info
        
    except Exception as e:
        logger.error(f"Error getting token info: {e}")
        return None

def get_market_data(token_id, days=90):
    """
    Obtiene datos históricos del token desde CoinGecko
    """
    #pasar a lowercase
    token_id = token_id.lower() 
    print("token_id "+token_id)
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{token_id}/market_chart"
        params = {
            "vs_currency": "usd",
            "days": days,
            "interval": "daily"
        }
        response = requests.get(url, params=params)
        if response.status_code != 200:
            logger.error(f"Error getting market data: {response.text}")
            return None
            
        return response.json()
    except Exception as e:
        logger.error(f"Error getting market data: {e}")
        return None

def process_data(data):
    if not data or "prices" not in data:
        return None
    
    df = pd.DataFrame(data["prices"], columns=["date", "price"])
    df["returns"] = df["price"].pct_change()
    return df

def calculate_volatility(df):
    if df is None or df.empty:
        return None, None
        
    daily_vol = df["returns"].std()
    annual_vol = daily_vol * np.sqrt(90)
    return daily_vol, annual_vol

def assess_risk(volatility, amount=None):
    print("volatility "+str(volatility))
    try:
        risk_level = "LOW"
        
        # Riesgo por volatilidad
        if volatility > 0.4:
            risk_level = "HIGH"
        elif volatility > 0.2:
            risk_level = "MEDIUM"
            
        # Ajustar por cantidad si está disponible
        if amount:
            amount_in_tokens = amount / 1e18
            if amount_in_tokens > 1000:
                risk_level = "HIGH"
            elif amount_in_tokens > 100 and risk_level != "HIGH":
                risk_level = "MEDIUM"
                
        return risk_level
    except Exception as e:
        logger.error(f"Error assessing risk: {e}")
        return "UNKNOWN"

def calculate_ash_risk(data: str):
    try:
        token_identifier, amount_hex = decode_data(data)
        if not token_identifier:
            return None
            
        # Obtener información del token
        token_info = get_token_id_from_identifier(token_identifier)
        if not token_info:
            logger.warning(f"No se pudo obtener información para el token {token_identifier}")
            return "UNKNOWN"
            
        # Obtener datos de mercado
        data = get_market_data(token_info["name"], days=90)  # 3 meses de datos
        if not data:
            return "UNKNOWN"
            
        # Procesar datos y calcular volatilidad
        df = process_data(data)
        daily_vol, annual_vol = calculate_volatility(df)
        
        if annual_vol is None:
            return "UNKNOWN"
            
        # Evaluar riesgo basado en volatilidad
        if annual_vol >= 0.4:
            risk_level = "HIGH"
        elif annual_vol >= 0.2:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
            
        logger.info(f"Risk Analysis - Token: {token_info['name']}, Volatility: {annual_vol:.4f}, Risk: {risk_level}")
        return risk_level
        
    except Exception as e:
        logger.error(f"Error calculating risk: {e}")
        return None 