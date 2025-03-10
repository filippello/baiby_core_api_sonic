from fastapi import WebSocket
from typing import List, Dict
import json
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.warnings: Dict[str, dict] = {}  # hash -> warning data

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Nueva conexión WebSocket. Total conexiones: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket desconectado. Conexiones restantes: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        logger.info(f"Intentando broadcast a {len(self.active_connections)} conexiones")
        disconnected = []
        
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
                logger.info(f"Mensaje enviado exitosamente a una conexión")
            except Exception as e:
                logger.error(f"Error en broadcast: {e}")
                disconnected.append(connection)
        
        # Limpiar conexiones desconectadas
        for conn in disconnected:
            await self.disconnect(conn)

    async def process_warning(self, warning_data: dict):
        tx_hash = warning_data.get("transaction_hash")
        if tx_hash:
            self.warnings[tx_hash] = warning_data
            # Notificar a la transacción que está esperando
            from app.routes import active_transactions
            event = active_transactions.get(tx_hash)
            if event:
                event.set()

    def get_warning(self, tx_hash: str) -> dict:
        return self.warnings.get(tx_hash)

    def clear_warning(self, tx_hash: str):
        self.warnings.pop(tx_hash, None)

ws_manager = WebSocketManager() 