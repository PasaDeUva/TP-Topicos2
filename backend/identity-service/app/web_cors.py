from starlette.middleware.cors import CORSMiddleware

from app.web_config import load_web_session_config


class WebCORSMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        try:
            origins = list(load_web_session_config().allowed_origins)
        except ValueError:
            origins = []
        middleware = CORSMiddleware(
            self.app,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["GET", "POST"],
            allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
        )
        await middleware(scope, receive, send)
