from aiogram import BaseMiddleware
from typing import Callable, Dict, Any, Awaitable

class ErrorsMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable[[Dict[str, Any]], Awaitable[Any]], event: Any, data: Dict[str, Any]) -> Any:
        try:
            return await handler(event, data)
        except Exception as e:
            # simple swallow; aiogram logs by default if configured
            raise
