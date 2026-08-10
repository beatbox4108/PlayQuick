# Privacy

PlayQuick has no analytics, telemetry, advertising, crash upload, or account
server. Local paths, metadata, favorites, history, queue, and session state stay
in the local SQLite database.

Spotify authorization tokens are stored in the operating system credential
store. Spotify metadata is held in memory for the active view and is not merged
into the local music library. Disconnecting Spotify deletes the stored token.

Debug logs must never contain OAuth authorization codes, access tokens, refresh
tokens, or HTTP Authorization headers.

