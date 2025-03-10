from pathlib import Path
import json
import os
import dotenv
import httpx
import asyncio
from multiversx_sdk import Account, DevnetEntrypoint, Transaction, Address, ProxyNetworkProvider
from multiversx_sdk.wallet import UserSigner

dotenv.load_dotenv()

# CONFIGURACIÓN
PROVIDER_URL = "https://testnet-gateway.multiversx.com"
API_URL = "http://localhost:8000/agent/transaction/"
RECEIVER_ADDRESS = "erd1md66ra4tfmpack774z6yfytwwn68azr43utsddv09v785wtqa9wq44kl46"
AMOUNT = 3.9555
#AMOUNT = 4.99895
GAS_LIMIT = 50000

provider = ProxyNetworkProvider(PROVIDER_URL)

def create_account():
    try:
        # Obtener la ruta absoluta del directorio actual
        current_dir = os.path.dirname(os.path.abspath(__file__))
        wallet_path = os.path.join(current_dir, "wallet.json")
        
        if not os.path.exists(wallet_path):
            raise FileNotFoundError(f"No se encuentra el archivo wallet.json en {wallet_path}")
            
        account = Account.new_from_keystore(
            file_path=Path(wallet_path),
            password=os.getenv("WALLET_PASSWORD")
        )
        account_on_network = provider.get_account(account.address)
        account.nonce = account_on_network.nonce
        return account
    except Exception as e:
        print(f"❌ Error creando la cuenta: {str(e)}")
        raise

async def send_transaction_to_api(transaction):
    tx_data = {
        "safeAddress": str(transaction.sender),
        "erc20TokenAddress": "EGLD",
        "reason": os.getenv('TRANSACTION_REASON', "need to transfer all EGLD, to start a new wallet"),
        "transactions": [{
            "to": str(transaction.receiver),
            "data": transaction.data.decode() if transaction.data else "",
            "value": str(transaction.value)
        }]
    }
    
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            timeout = httpx.Timeout(30.0, connect=20.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(API_URL, json=tx_data)
                response_data = response.json()
                print(f"Respuesta completa de la API: {response_data}")
                
                # Verificar si la transacción está aprobada basándonos en el mensaje
                message = response_data.get('message', '')
                is_approved = 'APPROVED' in message
                print(f"Mensaje de la API: {message}")
                print(f"¿Está aprobada? {is_approved}")
                
                if is_approved:
                    try:
                        # Enviar transacción a la blockchain
                        tx_hash = provider.send_transaction(transaction)
                        print(f"✅ Transacción aprobada y enviada. Hash: {tx_hash}")
                    except Exception as e:
                        print(f"❌ Error al enviar la transacción a la blockchain: {str(e)}")
                        raise
                else:
                    print(f"❌ Transacción rechazada: {message}")
                
                return response_data
                
        except httpx.ReadTimeout:
            if attempt < max_retries - 1:
                print(f"Timeout en intento {attempt + 1}. Reintentando en {retry_delay} segundos...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
            else:
                print("Error: No se pudo conectar después de varios intentos")
                raise
        except Exception as e:
            print(f"Error inesperado: {str(e)}")
            raise

if __name__ == "__main__":
    try:
        # Cargar cuenta
        account = create_account()
        
        # Crear transacción
        transaction = Transaction(
            nonce=account.nonce,
            sender=account.address,
            receiver=Address.new_from_bech32(RECEIVER_ADDRESS),
            value=int(AMOUNT * 10**18),
            gas_limit=GAS_LIMIT,
            chain_id="T",
            version=1
        )
        
        # Firmar transacción
        transaction.signature = account.sign_transaction(transaction)
        
        # Enviar a nuestra API primero
        result = asyncio.run(send_transaction_to_api(transaction))
        print(f"Respuesta de la API: {result}")
        
    except Exception as e:
        print(f"Error en la ejecución: {str(e)}")
    
    # Si todo está bien, enviar a la blockchain
    #tx_hash = provider.send_transaction(transaction)
    #print(f"Transacción enviada. Hash: {tx_hash}")
