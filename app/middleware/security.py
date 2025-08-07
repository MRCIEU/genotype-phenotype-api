from fastapi import Request
import re
from typing import Dict, Any
import html
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Middleware to sanitize input and query parameters
    """

    def __init__(self, app):
        super().__init__(app)
        # Regex for basic SQL injection patterns - fixed grouping
        self.sql_patterns = re.compile(
            r"('|\")?\s*([\0\b\'\"\n\r\t\%\_\\]*\s*((select\s*.+\s*from)|(insert\s*.+\s*into)|(update\s*.+\s*set)|(delete\s*.+\s*from)|(drop\s*.+)|(truncate\s*.+)|(alter\s*.+)|(exec\s*.+)|(\s*(all|any|not|and|between|in|like|or|some|contains|containsall|containskey)\s*.+[\=\>\<=\!\~]+)|(\s*[\/\*]+.*[\*\/]+)|([\s;\)]+-{2}[\s\w]*)|(\s*@.+=\s*\w+)|([\s\-\/]+.+[\s\-\/]+)))",
            re.IGNORECASE,
        )
        # Regex for special characters (adjust as needed)
        self.special_chars = re.compile(r"[<>{}[\]~`]")

    async def sanitize_input(self, value: Any) -> Any:
        """Sanitize a single input value"""
        if isinstance(value, str):
            # HTML escape to prevent XSS
            value = html.escape(value)
            # Remove SQL injection patterns
            value = self.sql_patterns.sub("", value)
            # Remove special characters
            value = self.special_chars.sub("", value)
            # Remove multiple spaces
            value = " ".join(value.split())
            return value.strip()
        elif isinstance(value, dict):
            return {k: await self.sanitize_input(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [await self.sanitize_input(item) for item in value]
        return value

    async def sanitize_query_params(self, query_params: Dict[str, str]) -> Dict[str, str]:
        """Sanitize query parameters"""
        return {k: await self.sanitize_input(v) for k, v in query_params.items()}

    async def dispatch(self, request: Request, call_next) -> Response:
        # Sanitize path parameters
        for param in request.path_params.values():
            sanitized_param = await self.sanitize_input(param)
            if sanitized_param != param:
                return Response(content="Invalid characters in request", status_code=400)

        # Sanitize query parameters
        query_params = dict(request.query_params)
        try:
            await self.sanitize_query_params(query_params)
        except Exception:
            return Response(content="Invalid query parameters", status_code=400)

        # Sanitize request body if it exists
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.json()
                sanitized_body = await self.sanitize_input(body)

                # Modify request body with sanitized content
                async def receive():
                    return {
                        "type": "http.request",
                        "body": str(sanitized_body).encode(),
                    }

                request._receive = receive
            except Exception:
                pass  # If body can't be parsed as JSON, let the route handler deal with it

        response = await call_next(request)
        return response
