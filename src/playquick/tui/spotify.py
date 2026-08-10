from __future__ import annotations

import webbrowser
from typing import ClassVar

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Input, Label, ListItem, ListView, Select, Static

from playquick.spotify.controller import SpotifyRemoteController
from playquick.spotify.models import SpotifyContainer, SpotifyPlayback, SpotifyTrack


class SpotifyStatus(Static):
    def update_playback(self, state: SpotifyPlayback | None) -> None:
        text = Text()
        text.append(" SPOTIFY REMOTE ", style="black on green bold")
        if state is None:
            text.append(" No active playback", style="dim")
        else:
            text.append(" ▶ " if state.playing else " Ⅱ ", style="green bold")
            text.append(state.track.name if state.track else "Unknown track", style="bold")
            if state.track:
                text.append(f" — {state.track.artist}", style="dim")
            if state.device:
                text.append(f"   on {state.device.name}", style="cyan")
        self.update(text)


class SpotifyScreen(Screen[None]):
    BINDINGS: ClassVar = [
        ("escape", "back", "Local"),
        ("ctrl+1", "back", "Local"),
        ("space", "play_pause", "Play/Pause"),
        ("a", "queue", "Add to queue"),
        ("n", "next", "Next"),
        ("b", "previous", "Previous"),
        ("slash", "search", "Search"),
        ("pageup", "previous_page", "Previous page"),
        ("pagedown", "next_page", "Next page"),
        ("o", "open", "Open in Spotify"),
    ]
    CSS = """
    #spotify-body { height: 1fr; }
    #spotify-sources { width: 22; border: solid $success; }
    #spotify-center { width: 1fr; }
    #spotify-search { dock: top; }
    #spotify-results { height: 2fr; border: solid $success; }
    #spotify-queue { height: 1fr; border: solid $secondary; }
    #spotify-status { height: 3; padding: 1; background: $surface; }
    """

    def __init__(self, controller: SpotifyRemoteController, *, extended: bool) -> None:
        super().__init__()
        self.controller = controller
        self.extended = extended
        self.tracks: list[SpotifyTrack] = []
        self.containers: list[SpotifyContainer] = []
        self.mode = "tracks"
        self.search_offset = 0
        self.search_query = ""

    def compose(self) -> ComposeResult:
        yield Label("Spotify Remote · Experimental · audio stays on Spotify Connect", id="notice")
        yield Select([], prompt="Spotify Connect device", id="spotify-device")
        with Horizontal(id="spotify-body"):
            yield ListView(
                ListItem(Label("Search"), id="spotify-source-search"),
                ListItem(Label("Saved Tracks"), id="spotify-source-saved"),
                ListItem(Label("Saved Albums"), id="spotify-source-albums"),
                ListItem(Label("My Playlists"), id="spotify-source-playlists"),
                ListItem(Label("Recently Played"), id="spotify-source-recent"),
                ListItem(Label("Top Tracks"), id="spotify-source-top"),
                id="spotify-sources",
            )
            with Vertical(id="spotify-center"):
                yield Input(placeholder="Search Spotify (10 results per page)", id="spotify-search")
                yield DataTable(id="spotify-results", cursor_type="row", zebra_stripes=True)
                yield DataTable(id="spotify-queue", cursor_type="row", zebra_stripes=True)
        yield SpotifyStatus("", id="spotify-status")
        yield Footer()

    async def on_mount(self) -> None:
        self.query_one("#spotify-results", DataTable).add_columns("Title", "Artist", "Album")
        self.query_one("#spotify-queue", DataTable).add_columns("Spotify queue", "Artist")
        try:
            devices = await self.controller.devices()
            selector = self.query_one("#spotify-device", Select)
            options = [(f"{device.name} ({device.type})", device.id) for device in devices]
            selector.set_options(options)
            active = next((device.id for device in devices if device.active), None)
            if active:
                selector.value = active
            if self.extended:
                await self._show_tracks(await self.controller.saved_tracks())
            await self._refresh_queue()
            await self._poll()
            self.set_interval(4, self._poll)
        except Exception as error:
            self.notify(
                f"Spotify is unavailable: {error}. Run 'playquick spotify login'.",
                severity="error",
                timeout=10,
            )

    async def _show_tracks(self, tracks: list[SpotifyTrack]) -> None:
        self.mode = "tracks"
        self.tracks = tracks
        self.containers = []
        table = self.query_one("#spotify-results", DataTable)
        table.clear()
        for track in tracks:
            table.add_row(track.name, track.artist, track.album, key=track.uri)

    async def _show_containers(self, containers: list[SpotifyContainer]) -> None:
        self.mode = "containers"
        self.containers = containers
        self.tracks = []
        table = self.query_one("#spotify-results", DataTable)
        table.clear()
        for container in containers:
            table.add_row(container.name, container.owner or "", container.kind, key=container.uri)

    async def _refresh_queue(self) -> None:
        tracks = await self.controller.client.queue()
        table = self.query_one("#spotify-queue", DataTable)
        table.clear()
        for track in tracks:
            table.add_row(track.name, track.artist)

    async def _poll(self) -> None:
        try:
            state = await self.controller.poll()
            self.query_one(SpotifyStatus).update_playback(state)
        except Exception as error:
            self.notify(f"Spotify state update failed: {error}", severity="warning")

    def selected_track(self) -> SpotifyTrack | None:
        row = self.query_one("#spotify-results", DataTable).cursor_row
        return self.tracks[row] if 0 <= row < len(self.tracks) else None

    def selected_container(self) -> SpotifyContainer | None:
        row = self.query_one("#spotify-results", DataTable).cursor_row
        return self.containers[row] if 0 <= row < len(self.containers) else None

    @on(Input.Submitted, "#spotify-search")
    async def submit_search(self, event: Input.Submitted) -> None:
        self.search_offset = 0
        self.search_query = event.value.strip()
        if self.search_query:
            await self._load_search_page()

    async def _load_search_page(self) -> None:
        tracks = await self.controller.search(
            self.search_query, offset=self.search_offset
        )
        await self._show_tracks(tracks)
        page = self.search_offset // 10 + 1
        self.notify(f"Spotify search page {page} ({len(tracks)} results)")

    @on(ListView.Selected, "#spotify-sources")
    async def source_selected(self, event: ListView.Selected) -> None:
        source = event.item.id
        try:
            if source == "spotify-source-saved":
                if not self.extended:
                    self.notify("Enable Spotify library scopes in Settings", severity="warning")
                    return
                await self._show_tracks(await self.controller.saved_tracks())
            elif source == "spotify-source-albums":
                if not self.extended:
                    self.notify("Enable Spotify library scopes in Settings", severity="warning")
                    return
                await self._show_containers(await self.controller.saved_albums())
            elif source == "spotify-source-playlists":
                if not self.extended:
                    self.notify("Enable Spotify library scopes in Settings", severity="warning")
                    return
                await self._show_containers(await self.controller.playlists())
            elif source == "spotify-source-recent":
                await self._show_tracks(await self.controller.recent())
            elif source == "spotify-source-top":
                await self._show_tracks(await self.controller.top_tracks())
            else:
                self.query_one("#spotify-search", Input).focus()
        except Exception as error:
            self.notify(f"Spotify request failed: {error}", severity="error")

    @on(DataTable.RowSelected, "#spotify-results")
    async def play_selected(self) -> None:
        if self.mode == "containers" and (container := self.selected_container()):
            content_id = container.uri.rsplit(":", 1)[-1]
            tracks = (
                await self.controller.album_tracks(content_id)
                if container.kind == "album"
                else await self.controller.playlist_tracks(content_id)
            )
            if tracks:
                await self._show_tracks(tracks)
            else:
                self.notify(
                    "Spotify did not expose this playlist's items; press o to open it",
                    severity="warning",
                )
        elif track := self.selected_track():
            await self.controller.play(track)
            self.notify(f"Sent to Spotify: {track.name}")

    @on(Select.Changed, "#spotify-device")
    async def device_selected(self, event: Select.Changed) -> None:
        if isinstance(event.value, str):
            await self.controller.transfer(event.value)
            self.notify("Spotify playback transferred")

    async def action_play_pause(self) -> None:
        state = self.controller.state
        if state and state.playing:
            await self.controller.pause()
        elif track := self.selected_track():
            await self.controller.play(track)

    async def action_queue(self) -> None:
        if track := self.selected_track():
            await self.controller.add_to_queue(track)
            await self._refresh_queue()
            self.notify(f"Added to Spotify queue: {track.name}")

    async def action_next(self) -> None:
        await self.controller.client.next()

    async def action_previous(self) -> None:
        await self.controller.client.previous()

    def action_search(self) -> None:
        self.query_one("#spotify-search", Input).focus()

    async def action_next_page(self) -> None:
        if not self.search_query:
            self.notify("Run a Spotify search first", severity="warning")
            return
        self.search_offset += 10
        await self._load_search_page()

    async def action_previous_page(self) -> None:
        if not self.search_query or self.search_offset == 0:
            return
        self.search_offset = max(0, self.search_offset - 10)
        await self._load_search_page()

    def action_open(self) -> None:
        track = self.selected_track()
        container = self.selected_container()
        url = track.external_url if track else container.external_url if container else None
        if url:
            webbrowser.open(url)

    async def action_back(self) -> None:
        await self.controller.close()
        self.app.pop_screen()
