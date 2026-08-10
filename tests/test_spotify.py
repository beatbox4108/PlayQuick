from __future__ import annotations

import time

import httpx
import pytest

from playquick.spotify.auth import OAuthToken, SpotifyAuth, create_challenge
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
