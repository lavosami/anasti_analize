import json
import os
from typing import Any

import aio_pika
from aio_pika.abc import AbstractIncomingMessage
from fastapi import HTTPException

from app.services.analysis_service import (
    build_analysis,
    category_parameters,
    correlation_parameters,
    group_rows,
    number_parameters,
)


AMQP_URL = os.getenv("AMQP_URL", "amqp://guest:guest@rabbitmq:5672/")
QUEUE_NAME = os.getenv("ANALYSIS_RPC_QUEUE", "analysis.rpc")


class AnalysisRpcServer:
    def __init__(self) -> None:
        self.connection: aio_pika.RobustConnection | None = None
        self.channel: aio_pika.abc.AbstractChannel | None = None
        self.queue: aio_pika.abc.AbstractQueue | None = None

    async def start(self) -> None:
        self.connection = await aio_pika.connect_robust(AMQP_URL)
        self.channel = await self.connection.channel()
        self.queue = await self.channel.declare_queue(QUEUE_NAME, durable=True)
        await self.queue.consume(self.handle_message)

    async def close(self) -> None:
        if self.channel is not None:
            await self.channel.close()
        if self.connection is not None:
            await self.connection.close()

    async def handle_message(self, message: AbstractIncomingMessage) -> None:
        async with message.process():
            response = await dispatch_request(json.loads(message.body))
            if not message.reply_to:
                return

            await self.channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(response).encode(),
                    correlation_id=message.correlation_id,
                    content_type="application/json",
                ),
                routing_key=message.reply_to,
            )


async def dispatch_request(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        action = payload["action"]
        data = payload.get("payload", {})

        if action == "analysis":
            result = build_analysis(data)
        elif action == "get_groups":
            result = group_rows(data)
        elif action == "number_params":
            result = number_parameters(data["values"])
        elif action == "category_params":
            result = category_parameters(data["values"])
        elif action == "correlation_params":
            result = correlation_parameters(data["data"])
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported analysis action: {action}")

        return {"status": "ok", "data": result}
    except HTTPException as exc:
        return {"status": "error", "error": {"status_code": exc.status_code, "detail": exc.detail}}
    except Exception as exc:
        return {"status": "error", "error": {"status_code": 500, "detail": str(exc)}}


analysis_rpc_server = AnalysisRpcServer()
