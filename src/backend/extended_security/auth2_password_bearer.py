from typing import Optional, cast

from fastapi import HTTPException, Request, WebSocket
from fastapi.requests import HTTPConnection
from fastapi.security import OAuth2PasswordBearer
from starlette.datastructures import MutableHeaders


class OAuth2PasswordBearerWsHttp(OAuth2PasswordBearer):
    async def __call__(self, request: HTTPConnection) -> Optional[str]:
        if isinstance(request, WebSocket):
            access_token = request.query_params.get("access_token", None)
            if access_token:
                new_header = MutableHeaders(request._headers)
                new_header["Authorization"] = f"Bearer {access_token}"
                request._headers = new_header
                request.scope.update(headers=request.headers.raw)
        try:
            return await super().__call__(
                request=cast(Request, request)  # Temp. dirty hack to make
                # it work with WS
            )
        except HTTPException:
            if isinstance(request, WebSocket):
                await request.close()
            raise
