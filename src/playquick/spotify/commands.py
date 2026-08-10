from __future__ import annotations

import asyncio

from playquick.config import ConfigStore
from playquick.spotify.auth import SpotifyAuth

BASE_SCOPES = (
    "user-read-playback-state",
    "user-read-currently-playing",
    "user-modify-playback-state",
)
LIBRARY_SCOPES = (
    "user-library-read",
    "user-read-recently-played",
    "user-top-read",
    "playlist-read-private",
)


def spotify_command(action: str) -> int:
    config = ConfigStore().load()
    if not config.spotify_client_id:
        print("Set spotify_client_id in the PlayQuick settings first.")
        return 2
    scopes = BASE_SCOPES + (LIBRARY_SCOPES if config.spotify_extended_library else ())
    auth = SpotifyAuth(config.spotify_client_id, scopes)
    if action == "login":
        asyncio.run(auth.login())
        print("Spotify account connected.")
    elif action == "logout":
        asyncio.run(auth.disconnect())
        print("Spotify account disconnected and local credentials removed.")
    return 0

