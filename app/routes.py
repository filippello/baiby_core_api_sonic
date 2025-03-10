from fastapi import APIRouter, HTTPException
from app.schemas import TransactionRequest, TransactionResponse
from app.websocket_manager import ws_manager
from app.config import settings
import hashlib
import asyncio
import httpx
import logging
import json
from typing import Dict

router = APIRouter()
logger = logging.getLogger(__name__)

# Diccionario para mantener el seguimiento de las transacciones activas
active_transactions: Dict[str, asyncio.Event] = {}

def serialize_transaction(tx_request: TransactionRequest) -> dict:
    return {
        "transactions": [
            {
                "to": tx.to,
                "data": tx.data,
                "value": tx.value
            } for tx in tx_request.transactions
        ],
        "safeAddress": tx_request.safeAddress,
        "erc20TokenAddress": tx_request.erc20TokenAddress,
        "reason": tx_request.reason
    }

async def send_to_tx_agent(transaction_data: dict, warning: str = None):
    try:
        try:
            jsonresp = json.loads(warning) if warning else {"message": "None", "status": "approved"}
            bot_reason = jsonresp.get('message')
            status = jsonresp.get('status')
        except Exception as e:
            logger.error(f"Error parseando warning: {e}")
            bot_reason = "None"
            status = "approved"
            warning = "nada"

        async with httpx.AsyncClient() as client:
            data = {
                "safeAddress": transaction_data["safeAddress"],
                "erc20TokenAddress": transaction_data["erc20TokenAddress"],
                "reason": transaction_data["reason"],
                "transactions": transaction_data["transactions"],
                'bot_reason': bot_reason,
                'status': status,
                "warning": warning
            }
            logger.info(f"Enviando a txAgent: {data}")
            response = await client.post(
                f"{settings.TX_AGENT_URL}", 
                json=data,
                timeout=20.0  # Aumentamos el timeout a 20 segundos
            )
            return response.json()
        
    except httpx.ConnectError:
        logger.error(f"No se pudo conectar a txAgent en {settings.TX_AGENT_URL}")
        return {"status": "error", "message": "txAgent no disponible"}
    except Exception as e:
        logger.error(f"Error al enviar a txAgent: {str(e)}")
        return {"status": "error", "message": str(e)}

async def process_transaction_with_timeout(tx_data: dict, transaction_hash: str):
    try:
        event = asyncio.Event()
        active_transactions[transaction_hash] = event
        
        try:
            logger.info(f"Esperando warnings para {transaction_hash}...")
            await asyncio.wait_for(event.wait(), timeout=10.0)
            warning = ws_manager.get_warning(transaction_hash)
            
            if warning:
                logger.info(f"Warning recibido para {transaction_hash}: {warning}")
                warning_data = json.dumps(warning)
                return await send_to_tx_agent(tx_data, warning_data)
            else:
                logger.info(f"No se recibió warning para {transaction_hash}, procediendo con aprobación")
                return {
                    "status": "success",
                    "message": "Transaction APPROVED - No warnings detected",
                    "approval_status": "APPROVED",
                    "llm_response": "No warnings detected"
                }
        except asyncio.TimeoutError:
            logger.info(f"Timeout alcanzado para {transaction_hash}, procediendo con aprobación por defecto")
            return {
                "status": "success",
                "message": "Transaction APPROVED - Timeout waiting for warnings",
                "approval_status": "APPROVED",
                "llm_response": "Timeout waiting for warnings"
            }
            
    finally:
        active_transactions.pop(transaction_hash, None)
        ws_manager.warnings.pop(transaction_hash, None)

@router.post("/agent/transaction/", response_model=TransactionResponse)
async def process_agent_transaction(transaction: TransactionRequest):
    try:
        # Serializar la transacción
        tx_data = serialize_transaction(transaction)
        
        # Generar hash
        transaction_hash = hashlib.sha256(
            json.dumps(tx_data, sort_keys=True).encode()
        ).hexdigest()
        
        # Preparar mensaje para los bots
        tx_message = {
            "type": "transaction",
            "data": {
                "transactions": tx_data["transactions"],
                "hash": transaction_hash,
                "safewallet": tx_data["safeAddress"]
            }
        }
        
        # Broadcast a los bots
        await ws_manager.broadcast(tx_message)
        
        # Esperar el resultado del procesamiento y obtener la respuesta
        tx_agent_response = await process_transaction_with_timeout(tx_data, transaction_hash)
        
        return TransactionResponse(
            status="success",
            message=f"Transaction {tx_agent_response.get('approval_status', 'PENDING')} - {tx_agent_response.get('llm_response', '')}",
            transaction_hash=transaction_hash,
            approval_status=tx_agent_response.get('approval_status', 'PENDING')
        )
    except Exception as e:
        logger.error(f"Error en process_agent_transaction: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing transaction: {str(e)}"
        ) 