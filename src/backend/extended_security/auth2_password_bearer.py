from typing import Optional, cast

from fastapi import HTTPException, Request, WebSocket
from fastapi.requests import HTTPConnection
from fastapi.security import OAuth2PasswordBearer


class OAuth2PasswordBearerWsHttp(OAuth2PasswordBearer):
    async def __call__(self, request: HTTPConnection) -> Optional[str]:
        try:
            return await super().__call__(
                request=cast(Request, request)  # Temp. dirty hack to make
                # it work with WS
            )
        except HTTPException:
            if isinstance(request, WebSocket):
                await request.close()
            raise
