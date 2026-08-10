from __future__ import annotations

import asyncio
import os
import webbrowser

import httpx

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


def spotify_command(action: str, *, open_browser: bool = True) -> int:
    config = ConfigStore().load()
    if not config.spotify_client_id:
        print("Set spotify_client_id in the PlayQuick settings first.")
        return 2
    scopes = BASE_SCOPES + (LIBRARY_SCOPES if config.spotify_extended_library else ())
    auth = SpotifyAuth(config.spotify_client_id, scopes)
    if action == "login":
        request = auth.begin_login()
        print("Open this URL in a browser and approve access:\n")
        print(request.url)
        print("\nAfter authorization, paste the full callback URL below.")
        remote_session = any(
            os.environ.get(name) for name in ("SSH_CLIENT", "SSH_CONNECTION", "SSH_TTY")
        )
        if open_browser and not remote_session:
            try:
                webbrowser.open(request.url)
            except webbrowser.Error:
                print("Could not open a browser; use the authorization URL printed above.")
        try:
            callback_url = input("Callback URL: ").strip()
            asyncio.run(auth.complete_login(request, callback_url))
        except (EOFError, ValueError, RuntimeError, httpx.HTTPError) as error:
            print(f"Spotify authorization failed: {error}")
            return 1
        print("Spotify account connected.")
    elif action == "logout":
        asyncio.run(auth.disconnect())
        print("Spotify account disconnected and local credentials removed.")
    return 0
