from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import secrets
import time
import urllib.parse
from contextlib import suppress
from dataclasses import asdict, dataclass
from typing import Protocol

import httpx
import keyring

AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
SERVICE_NAME = "PlayQuick"
DEFAULT_REDIRECT_URI = "https://beatbox4108.github.io/PlayQuick/spotify-callback/"


@dataclass(slots=True)
class OAuthToken:
    access_token: str
    refresh_token: str
    expires_at: float
    scope: str

    @property
    def expired(self) -> bool:
        return time.time() >= self.expires_at - 30


@dataclass(slots=True, frozen=True)
class AuthorizationRequest:
    url: str
    redirect_uri: str
    verifier: str
    state: str


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


class SpotifyAuth:
    def __init__(
        self,
        client_id: str,
        scopes: tuple[str, ...],
        *,
        redirect_uri: str = DEFAULT_REDIRECT_URI,
        store: TokenStore | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.client_id = client_id
        self.scopes = scopes
        self.redirect_uri = redirect_uri
        self.store = store or KeyringTokenStore()
        self.client = client or httpx.AsyncClient(timeout=30)

    async def token(self) -> str:
        token = await asyncio.to_thread(self.store.load)
        if token is None:
            raise RuntimeError("Spotify is not connected")
        if token.expired:
            token = await self.refresh(token)
        return token.access_token

    def begin_login(self) -> AuthorizationRequest:
        verifier = create_verifier()
        state = secrets.token_urlsafe(24)
        query = urllib.parse.urlencode(
            {
                "client_id": self.client_id,
                "response_type": "code",
                "redirect_uri": self.redirect_uri,
                "scope": " ".join(self.scopes),
                "state": state,
                "code_challenge_method": "S256",
                "code_challenge": create_challenge(verifier),
            }
        )
        return AuthorizationRequest(
            url=f"{AUTH_URL}?{query}",
            redirect_uri=self.redirect_uri,
            verifier=verifier,
            state=state,
        )

    async def complete_login(self, request: AuthorizationRequest, callback_url: str) -> OAuthToken:
        callback = urllib.parse.urlparse(callback_url.strip())
        expected = urllib.parse.urlparse(request.redirect_uri)
        if (callback.scheme, callback.netloc, callback.path) != (
            expected.scheme,
            expected.netloc,
            expected.path,
        ):
            raise ValueError("The pasted URL is not the PlayQuick Spotify callback URL")
        values = {
            key: items[0] for key, items in urllib.parse.parse_qs(callback.query).items() if items
        }
        if values.get("state") != request.state:
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
                "redirect_uri": request.redirect_uri,
                "code_verifier": request.verifier,
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
