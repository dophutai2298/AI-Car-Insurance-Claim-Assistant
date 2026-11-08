from fastapi.staticfiles import StaticFiles
from starlette.datastructures import Headers
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response
from starlette.types import Scope


class SpaStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as error:
            accept = Headers(scope=scope).get("accept", "")
            accepts_html = "text/html" in accept or "application/xhtml+xml" in accept
            is_api_path = path == "api" or path.startswith("api/")
            if (
                error.status_code != 404
                or is_api_path
                or scope["method"] not in {"GET", "HEAD"}
                or not accepts_html
            ):
                raise
            return await super().get_response("index.html", scope)
