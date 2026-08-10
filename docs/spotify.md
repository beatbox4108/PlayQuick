# Spotify Remote (experimental)

Spotify Remote controls official Spotify clients and Connect devices. PlayQuick
does not download, decode, record, mix, or persist Spotify audio.

## Setup

1. Use a Spotify Premium account to create an application in the Spotify
   Developer Dashboard.
2. Register `http://127.0.0.1/callback` as a loopback redirect URI. Spotify may
   permit the authorization request to add the temporary local port.
3. Paste the Client ID into PlayQuick Settings. Do not provide a Client Secret.
4. Enable library scopes only if Saved Tracks, Recently Played, and Top Tracks
   are wanted.
5. Run `uv run playquick spotify login` and approve the requested scopes.

Use `uv run playquick spotify logout` to remove the locally stored token. The
token is kept in the operating system credential store, never in `config.toml`.

Development Mode limits, endpoint availability, playlist visibility, Premium
requirements, and quotas are controlled by Spotify and can change independently
of PlayQuick. Public or editorial playlist contents may be unavailable. Spotify
search is intentionally paged in groups of ten.

