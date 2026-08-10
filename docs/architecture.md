# Architecture

PlayQuick separates five boundaries:

1. Textual views render typed state and dispatch user intent.
2. The library repository owns SQLite and migrations.
3. The scanner extracts local metadata with Mutagen.
4. Local playback uses a separate mpv process over JSON IPC.
5. Spotify Remote uses Web API commands and never implements local audio playback.

The local queue and Spotify queue deliberately have different models. Spotify's
queue is display/add-only because its Web API does not expose arbitrary removal
or reordering.

