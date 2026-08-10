from __future__ import annotations

import time
import urllib.parse

import httpx
import pytest

from playquick.spotify.auth import (
    DEFAULT_REDIRECT_URI,
    OAuthToken,
    SpotifyAuth,
    create_challenge,
)
from playquick.spotify.client import SpotifyClient


class MemoryStore:
    def __init__(self) -> None:
        self.value: OAuthToken | None = OAuthToken("token", "refresh", time.time() + 3600, "")

    def load(self) -> OAuthToken | None:
        return self.value

    def save(self, token: OAuthToken) -> None:
        self.value = token

    def clear(self) -> None:
        self.value = None


def test_pkce_challenge_is_url_safe() -> None:
    challenge = create_challenge("a" * 64)
    assert "=" not in challenge
    assert "+" not in challenge


def test_login_request_uses_static_callback_and_pkce() -> None:
    request = SpotifyAuth("client", ("scope",), store=MemoryStore()).begin_login()
    query = urllib.parse.parse_qs(urllib.parse.urlparse(request.url).query)

    assert query["redirect_uri"] == [DEFAULT_REDIRECT_URI]
    assert query["code_challenge_method"] == ["S256"]
    assert query["state"] == [request.state]


@pytest.mark.asyncio
async def test_login_completes_from_pasted_callback_url() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        form = urllib.parse.parse_qs(request.content.decode())
        assert form["code"] == ["authorization-code"]
        assert form["redirect_uri"] == [DEFAULT_REDIRECT_URI]
        return httpx.Response(
            200,
            json={
                "access_token": "new-token",
                "refresh_token": "new-refresh",
                "expires_in": 3600,
                "scope": "scope",
            },
        )

    store = MemoryStore()
    auth = SpotifyAuth(
        "client",
        ("scope",),
        store=store,
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    request = auth.begin_login()
    callback = f"{DEFAULT_REDIRECT_URI}?code=authorization-code&state={request.state}"

    token = await auth.complete_login(request, callback)

    assert token.access_token == "new-token"
    assert store.value == token


@pytest.mark.asyncio
async def test_login_rejects_callback_with_wrong_state() -> None:
    auth = SpotifyAuth("client", (), store=MemoryStore())
    request = auth.begin_login()

    with pytest.raises(RuntimeError, match="state mismatch"):
        await auth.complete_login(
            request,
            f"{DEFAULT_REDIRECT_URI}?code=authorization-code&state=wrong",
        )


@pytest.mark.asyncio
async def test_login_rejects_callback_from_another_site() -> None:
    auth = SpotifyAuth("client", (), store=MemoryStore())
    request = auth.begin_login()

    with pytest.raises(ValueError, match="not the PlayQuick Spotify callback"):
        await auth.complete_login(
            request,
            f"https://example.test/callback?code=code&state={request.state}",
        )


@pytest.mark.asyncio
async def test_search_tolerates_missing_fields() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer token"
        return httpx.Response(
            200,
            json={"tracks": {"items": [{"uri": "spotify:track:1", "name": "Song"}]}},
        )

    store = MemoryStore()
    auth = SpotifyAuth("client", (), store=store)
    client = SpotifyClient(
        auth,
        httpx.AsyncClient(
            base_url="https://api.spotify.test", transport=httpx.MockTransport(handler)
        ),
    )
    tracks = await client.search("Song")
    assert tracks[0].artist == "Unknown Artist"
    assert tracks[0].uri == "spotify:track:1"


@pytest.mark.asyncio
async def test_player_commands_accept_empty_response() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(204)

    auth = SpotifyAuth("client", (), store=MemoryStore())
    client = SpotifyClient(
        auth,
        httpx.AsyncClient(
            base_url="https://api.spotify.test", transport=httpx.MockTransport(handler)
        ),
    )
    await client.play(uri="spotify:track:1")


@pytest.mark.asyncio
async def test_rate_limit_retries_once() -> None:
    calls = 0

    async def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(200, json={"devices": []})

    auth = SpotifyAuth("client", (), store=MemoryStore())
    client = SpotifyClient(
        auth,
        httpx.AsyncClient(
            base_url="https://api.spotify.test", transport=httpx.MockTransport(handler)
        ),
    )
    assert await client.devices() == []
    assert calls == 2
