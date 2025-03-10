import asyncio
import websockets
import json
import logging
from datetime import datetime
import traceback
from web3 import Web3
from risk_function import calculate_risk
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
WS_BOT_URL = os.getenv('WS_BOT_URL', 'ws://localhost:8000/ws/bot')  # URL por defecto como fallback
RPC_URL = os.getenv('RPC_URL')

w3 = Web3(Web3.HTTPProvider(RPC_URL))

async def monitor_transactions():
    uri = WS_BOT_URL
    
    while True:  # Bucle principal para reconexión
        try:
            async with websockets.connect(uri) as websocket:
                logger.info(f"✅ Bot conectado al servidor en {uri}")
                
                while True:
                    try:
                        message = await websocket.recv()
                        logger.info(f"📩 Mensaje recibido: {message}")
                        
                        data = json.loads(message)
                        logger.info(f"🔄 Datos parseados: {data}")
                        
                        if data.get("type") == "transaction":
                            transactions = data.get("data", {}).get("transactions", [])
                            transaction_hash = data.get("data", {}).get("hash")
                            
                            logger.info(f"🔍 Analizando transacciones: {transactions}")
                            
                            # Verificar cada transacción
                            for tx in transactions:
                                tx_data = tx.get("data", "")
                                risk_result = calculate_risk(tx_data)
                                
                                if risk_result is not None:
                                    warning = {
                                        "type": "warning",
                                        "message": f"investment risk is: {risk_result}",
                                        "transaction_hash": transaction_hash,
                                        "status": "warning",
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
        logger.info("🤖 Iniciando bot de riesgo...")
        asyncio.run(monitor_transactions())
    except KeyboardInterrupt:
        logger.info("👋 Bot detenido por el usuario")