import asyncio
import websockets
import json
import logging
from datetime import datetime
from goplus.address import Address
import traceback
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

async def check_address_security(address: str) -> tuple[bool, str]:
    try:
        logger.info(f"🔍 Checking address: {address}")
        response = Address(access_token=None).address_security(address=address)
        data = response.__dict__
        logger.info(f"📝 GoPlus response: {data}")
        
        # Convertimos el _result a diccionario también
        result = data.get("_result").__dict__ if data.get("_result") else {}
        if not result:
            return False, "Error: No result data"
        
        # Filtrar las categorías que tienen valor "1"
        flagged_categories = [
            category.replace("_", " ").title()
            for category, value in result.items()
            if value == "1" and category not in ["data_source", "contract_address"]
        ]
        
        logger.info(f"🏷️ Categorías detectadas: {flagged_categories}")
        
        if flagged_categories:
            warning_message = "Warning: destination address is flagged with these categories: " + ", ".join(flagged_categories)
            return True, warning_message
        
        return False, ""
        
    except Exception as e:
        logger.error(f"Error checking address security: {e}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return False, f"Error checking address: {str(e)}"

async def monitor_transactions():
    uri = WS_BOT_URL
    
    while True:  # Bucle principal para reconexión
        try:
            async with websockets.connect(uri) as websocket:
                logger.info(f"✅ Bot conectado al servidor en {uri}")
                
                while True:
                    try:
                        # Recibir mensaje
                        message = await websocket.recv()
                        logger.info(f"📩 Mensaje recibido: {message}")
                        
                        data = json.loads(message)
                        logger.info(f"🔄 Datos parseados: {data}")
                        
                        if data.get("type") == "transaction":
                            transactions = data.get("data", {}).get("transactions", [])
                            transaction_hash = data.get("data", {}).get("hash")
                            safewallet = data.get("data", {}).get("safewallet")
                            
                            logger.info(f"🔍 Analizando transacciones para safewallet: {safewallet}")
                            logger.info(f"🔍 Analizando transacciones: {transactions}")
                            logger.info(f"📝 Hash de transacción: {transaction_hash}")
                            
                            # Verificar cada transacción con GoPlus
                            for tx in transactions:
                                destination_address = tx.get("to")
                                logger.info(f"📍 Dirección destino: {destination_address}")
                                if not destination_address:
                                    logger.warning("⚠️ No se encontró dirección destino")
                                    continue
                                    
                                is_malicious, warning_message = await check_address_security(destination_address)
                                logger.info(f"🚨 Resultado del check: malicioso={is_malicious}, mensaje={warning_message}")
                                
                                if is_malicious:
                                    warning = {
                                        "type": "warning",
                                        "message": warning_message,
                                        "transaction_hash": transaction_hash,
                                        "status": "warning",
                                        "timestamp": datetime.utcnow().isoformat()
                                    }
                                    
                                    # Enviar warning
                                    await websocket.send(json.dumps(warning))
                                    logger.info(f"⚠️ Warning enviado: {warning}")
                                    break  # Solo enviamos un warning por lote de transacciones
                    
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