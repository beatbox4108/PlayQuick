from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import secrets
import threading
import time
import urllib.parse
import webbrowser
from contextlib import suppress
from dataclasses import asdict, dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import ClassVar, Protocol

import httpx
import keyring

AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
SERVICE_NAME = "PlayQuick"


@dataclass(slots=True)
class OAuthToken:
    access_token: str
    refresh_token: str
    expires_at: float
    scope: str

    @property
    def expired(self) -> bool:
        return time.time() >= self.expires_at - 30


class TokenStore(Protocol):
    def load(self) -> OAuthToken | None: ...
    def save(self, token: OAuthToken) -> None: ...
    def clear(self) -> None: ...


class KeyringTokenStore:
    def __init__(self, account: str = "spotify") -> None:
        self.account = account

    def load(self) -> OAuthToken | None:
        value = keyring.get_password(SERVICE_NAME, self.account)
        return OAuthToken(**json.loads(value)) if value else None

    def save(self, token: OAuthToken) -> None:
        keyring.set_password(SERVICE_NAME, self.account, json.dumps(asdict(token)))

    def clear(self) -> None:
        with suppress(keyring.errors.PasswordDeleteError):
            keyring.delete_password(SERVICE_NAME, self.account)


def create_verifier() -> str:
    return secrets.token_urlsafe(64)


def create_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


class _CallbackHandler(BaseHTTPRequestHandler):
    values: ClassVar[dict[str, str]] = {}
    event: ClassVar[threading.Event] = threading.Event()

    def do_GET(self) -> None:
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        type(self).values = {key: values[0] for key, values in query.items() if values}
        body = b"PlayQuick authorization received. You can close this window."
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        type(self).event.set()

    def log_message(self, _format: str, *_args: object) -> None:
        return


class SpotifyAuth:
    def __init__(
        self,
        client_id: str,
        scopes: tuple[str, ...],
        *,
        store: TokenStore | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.client_id = client_id
        self.scopes = scopes
        self.store = store or KeyringTokenStore()
        self.client = client or httpx.AsyncClient(timeout=30)

    async def token(self) -> str:
        token = await asyncio.to_thread(self.store.load)
        if token is None:
            raise RuntimeError("Spotify is not connected")
        if token.expired:
            token = await self.refresh(token)
        return token.access_token

    async def login(self) -> OAuthToken:
        verifier = create_verifier()
        state = secrets.token_urlsafe(24)
        _CallbackHandler.values = {}
        _CallbackHandler.event.clear()
        server = HTTPServer(("127.0.0.1", 0), _CallbackHandler)
        redirect_uri = f"http://127.0.0.1:{server.server_port}/callback"
        query = urllib.parse.urlencode(
            {
                "client_id": self.client_id,
                "response_type": "code",
                "redirect_uri": redirect_uri,
                "scope": " ".join(self.scopes),
                "state": state,
                "code_challenge_method": "S256",
                "code_challenge": create_challenge(verifier),
            }
        )
        webbrowser.open(f"{AUTH_URL}?{query}")
        try:
            await asyncio.wait_for(asyncio.to_thread(server.handle_request), timeout=180)
        finally:
            server.server_close()
        values = _CallbackHandler.values
        if values.get("state") != state:
            raise RuntimeError("Spotify OAuth state mismatch")
        if error := values.get("error"):
            raise RuntimeError(f"Spotify authorization failed: {error}")
        code = values.get("code")
        if not code:
            raise RuntimeError("Spotify did not return an authorization code")
        response = await self.client.post(
            TOKEN_URL,
            data={
                "client_id": self.client_id,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "code_verifier": verifier,
            },
        )
        response.raise_for_status()
        token = self._parse_token(response.json())
        await asyncio.to_thread(self.store.save, token)
        return token

    async def refresh(self, token: OAuthToken) -> OAuthToken:
        response = await self.client.post(
            TOKEN_URL,
            data={
                "client_id": self.client_id,
                "grant_type": "refresh_token",
                "refresh_token": token.refresh_token,
            },
        )
        response.raise_for_status()
        value = response.json()
        value.setdefault("refresh_token", token.refresh_token)
        value.setdefault("scope", token.scope)
        refreshed = self._parse_token(value)
        await asyncio.to_thread(self.store.save, refreshed)
        return refreshed

    async def disconnect(self) -> None:
        await asyncio.to_thread(self.store.clear)

    @staticmethod
    def _parse_token(value: dict[str, object]) -> OAuthToken:
        return OAuthToken(
            access_token=str(value["access_token"]),
            refresh_token=str(value.get("refresh_token", "")),
            expires_at=time.time() + int(str(value.get("expires_in", 3600))),
            scope=str(value.get("scope", "")),
        )
