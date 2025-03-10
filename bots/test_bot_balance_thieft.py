import asyncio
import websockets
import json
import logging
from datetime import datetime
import traceback
from web3 import Web3
from dotenv import load_dotenv
import os

# Cargar variables de entorno
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuración desde variables de entorno
RPC_URL = os.getenv('RPC_URL')
WS_BOT_URL = os.getenv('WS_BOT_URL', 'ws://localhost:8000/ws/bot')  # URL por defecto como fallback

w3 = Web3(Web3.HTTPProvider(RPC_URL))

async def get_native_balance(address: str) -> int:
    try:
        logger.info(f"🔍 Intentando obtener balance para {address}")
        if not w3.is_address(address):
            logger.error(f"❌ Dirección inválida: {address}")
            return 0
            
        balance = w3.eth.get_balance(address)
        logger.info(f"💰 Balance nativo obtenido para {address}: {balance}")
        return balance
    except Exception as e:
        logger.error(f"❌ Error obteniendo balance: {e}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return 0

def parse_value(value_str):
    try:
        # Remover los decimales y cualquier punto
        clean_value = value_str.split('.')[0]
        
        # Verificar si es hexadecimal
        if clean_value.startswith("0x"):
            return int(clean_value, 16)
        else:
            return int(clean_value)
    except Exception as e:
        logger.error(f"Error parsing value {value_str}: {e}")
        return 0

async def monitor_transactions():
    uri = WS_BOT_URL
    
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                logger.info(f"✅ Bot connected to server at {uri}")
                
                while True:
                    try:
                        message = await websocket.recv()
                        logger.info(f"📩 Message received: {message}")
                        
                        data = json.loads(message)
                        logger.info(f"🔄 Parsed data: {data}")
                        
                        if data.get("type") == "transaction":
                            transactions = data.get("data", {}).get("transactions", [])
                            transaction_hash = data.get("data", {}).get("hash")
                            safewallet = data.get("data", {}).get("safewallet")
                            
                            logger.info(f"🔍 Analizando transacción para safewallet: {safewallet}")
                            
                            if not safewallet:
                                logger.warning("⚠️ No se encontró safewallet en el mensaje")
                                continue
                                
                            # Obtener balance nativo
                            current_balance = await get_native_balance(safewallet)
                            logger.info(f"💰 Balance actual: {current_balance}")
                            
                            # Verificar cada transacción
                            for tx in transactions:
                                # Usar la nueva función para parsear el valor
                                value = parse_value(tx.get("value", "0"))
                                
                                logger.info(f"💱 Valor de la transacción: {value}")
                                
                                if value > current_balance*0.99 and value > 0:
                                    warning = {
                                        "type": "warning",
                                        "message": f"⚠️ Posible vaciado de wallet detectado! La transacción usa todo el balance nativo ({value} wei)",
                                        "transaction_hash": transaction_hash,
                                        "status": "warning",
                                        "safewallet": safewallet,
                                        "current_balance": str(current_balance),
                                        "tx_value": str(value),
                                        "timestamp": datetime.utcnow().isoformat()
                                    }
                                    
                                    await websocket.send(json.dumps(warning))
                                    logger.info(f"⚠️ Warning enviado: {warning}")
                                    break
                    
                    except websockets.ConnectionClosed:
                        logger.warning("❌ Conexión cerrada. Intentando reconectar...")
                        break
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ Error decodificando JSON: {e}")
                        continue
                    except Exception as e:
                        logger.error(f"❌ Error inesperado: {e}")
                        logger.error(f"Stack trace: {traceback.format_exc()}")
                        continue
                        
        except Exception as e:
            logger.error(f"❌ Error de conexión: {e}")
            logger.info("🔄 Intentando reconectar en 5 segundos...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        logger.info("🤖 Iniciando bot...")
        asyncio.run(monitor_transactions())
    except KeyboardInterrupt:
        logger.info("👋 Bot detenido por el usuario")