from __future__ import annotations

import asyncio
from pathlib import Path
from typing import ClassVar

from textual import events, on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, Input, Label, ListItem, ListView

from playquick.config import AppConfig, ConfigStore, default_database_path
from playquick.library import LibraryScanner
from playquick.models import PlaybackStatus, RepeatMode, Track
from playquick.playback.mpv import MpvController
from playquick.playback.queue import PlaybackQueue
from playquick.playback.session import PlaybackSession
from playquick.runtime.mpv_manager import MpvRuntimeManager
from playquick.spotify.auth import SpotifyAuth
from playquick.spotify.client import SpotifyClient
from playquick.spotify.commands import BASE_SCOPES, LIBRARY_SCOPES
from playquick.spotify.controller import SpotifyRemoteController
from playquick.storage import Database, LibraryRepository
from playquick.tui.screens import HelpScreen, MpvSetupScreen, SettingsScreen, install_mpv
from playquick.tui.spotify import SpotifyScreen
from playquick.tui.widgets import PlayerBar


class PlayQuickApp(App[None]):
    TITLE = "PlayQuick"
    CSS = """
    #body { height: 1fr; }
    #sources { width: 22; border: solid $primary; }
    #center { width: 1fr; }
    #library { height: 2fr; border: solid $primary; }
    #queue { height: 1fr; border: solid $secondary; }
    #search { display: none; dock: top; }
    #search.visible { display: block; }
    PlayerBar { height: 3; padding: 1; background: $surface; }
    #help-dialog, #mpv-dialog, #settings-dialog {
      width: 70; height: auto; padding: 1 2;
      border: thick $primary; background: $surface;
    }
    ModalScreen { align: center middle; background: $background 70%; }
    .compact #sources { width: 15; }
    .compact #queue { display: none; }
    """
    BINDINGS: ClassVar = [
        ("ctrl+q", "quit_app", "Quit"),
        ("ctrl+2", "spotify", "Spotify"),
        ("space", "toggle_pause", "Play/Pause"),
        ("a", "queue_append", "Queue"),
        ("A", "queue_next", "Play next"),
        ("n", "next_track", "Next"),
        ("b", "previous_track", "Previous"),
        ("left", "seek(-5)", "-5s"),
        ("right", "seek(5)", "+5s"),
        ("shift+left", "seek(-30)", "-30s"),
        ("shift+right", "seek(30)", "+30s"),
        ("slash", "search", "Filter"),
        ("ctrl+f", "search", "Search"),
        ("u", "undo", "Undo"),
        ("delete", "queue_delete", "Remove"),
        ("ctrl+up", "queue_move(-1)", "Move up"),
        ("ctrl+down", "queue_move(1)", "Move down"),
        ("f", "favorite", "Favorite"),
        ("question_mark", "help", "Help"),
        ("comma", "settings", "Settings"),
        ("plus", "volume(5)", "Volume +"),
        ("minus", "volume(-5)", "Volume -"),
        ("0", "mute", "Mute"),
        ("s", "shuffle", "Shuffle"),
        ("r", "repeat", "Repeat"),
        ("j", "cursor_down", "Down"),
        ("k", "cursor_up", "Up"),
    ]

    def __init__(
        self,
        *,
        database_path: Path | None = None,
        config_path: Path | None = None,
        setup_prompt: bool = True,
    ) -> None:
        super().__init__()
        self.config_store = ConfigStore(config_path)
        self.config = self.config_store.load()
        self.database = Database(database_path or default_database_path())
        self.database.migrate()
        self.repository = LibraryRepository(self.database)
        self.queue = PlaybackQueue(self.repository)
        configured = Path(self.config.mpv_path) if self.config.mpv_path else None
        self.runtime = MpvRuntimeManager(configured_path=configured)
        self.controller: MpvController | None = None
        self.session: PlaybackSession | None = None
        self._tracks: list[Track] = []
        self._setup_prompt = setup_prompt
        self.dark = self.config.theme != "light"

    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(placeholder="Search title, artist, album, or genre", id="search")
        with Horizontal(id="body"):
            yield ListView(
                ListItem(Label("All Tracks"), id="source-all"),
                ListItem(Label("Albums"), id="source-albums"),
                ListItem(Label("Artists"), id="source-artists"),
                ListItem(Label("Genres"), id="source-genres"),
                ListItem(Label("Folders"), id="source-folders"),
                ListItem(Label("Playlists"), id="source-playlists"),
                ListItem(Label("Favorites"), id="source-favorites"),
                ListItem(Label("History"), id="source-history"),
                ListItem(Label("Spotify Remote"), id="source-spotify"),
                id="sources",
            )
            with Vertical(id="center"):
                yield DataTable(id="library", cursor_type="row", zebra_stripes=True)
                yield DataTable(id="queue", cursor_type="row", zebra_stripes=True)
        yield PlayerBar(id="player")
        yield Footer()

    async def on_mount(self) -> None:
        library = self.query_one("#library", DataTable)
        library.add_columns("Title", "Artist", "Album", "Time")
        queue = self.query_one("#queue", DataTable)
        queue.add_columns("Up next", "Artist")
        self.load_tracks(self.repository.tracks())
        self.refresh_queue()
        if self.config.music_dirs:
            self.run_worker(self._scan_configured(), name="library-scan", exclusive=True)
        executable = self.runtime.resolve()
        if executable:
            await self._start_player(executable)
        elif self._setup_prompt:
            self.push_screen(MpvSetupScreen(), self._mpv_setup_result)
        self.set_interval(1.0, self._poll_player)

    async def _scan_configured(self) -> None:
        roots = [Path(value) for value in self.config.music_dirs]
        result = await asyncio.to_thread(LibraryScanner(self.database).scan, roots)
        self.load_tracks(self.repository.tracks())
        self.notify(
            f"Library scan: {result.added} added, {result.updated} updated, "
            f"{result.missing} missing"
        )
        if result.errors:
            self.notify(
                f"Library scan completed with {len(result.errors)} warnings",
                severity="warning",
            )

    def on_resize(self, event: events.Resize) -> None:
        self.set_class(event.size.width < 70, "compact")

    def _mpv_setup_result(self, download: bool | None) -> None:
        if download:
            self.run_worker(
                install_mpv(self.runtime, self._mpv_installed_callback),
                exclusive=True,
                name="install-mpv",
            )

    def _mpv_installed_callback(self, path: Path) -> None:
        self.call_later(self._start_player, path)

    async def _start_player(self, executable: Path) -> None:
        try:
            self.controller = MpvController(executable)
            await self.controller.start()
            self.session = PlaybackSession(self.controller, self.repository, self.queue)
            self.notify(f"Using mpv: {executable}")
        except Exception as error:
            self.controller = None
            self.session = None
            self.notify(f"Could not start mpv: {error}", severity="error")

    async def _poll_player(self) -> None:
        if not self.controller or self.controller.state.status == PlaybackStatus.STOPPED:
            return
        try:
            state = await self.controller.poll()
            self.query_one(PlayerBar).state = state
        except Exception as error:
            state = self.controller.state
            state.status = PlaybackStatus.ERROR
            state.error = str(error)
            self.query_one(PlayerBar).state = state

    def load_tracks(self, tracks: list[Track]) -> None:
        self._tracks = tracks
        table = self.query_one("#library", DataTable)
        table.clear()
        for track in tracks:
            minutes, seconds = divmod(int(track.duration), 60)
            table.add_row(
                track.title,
                track.artist,
                track.album,
                f"{minutes}:{seconds:02d}",
                key=str(track.id),
            )

    def selected_track(self) -> Track | None:
        table = self.query_one("#library", DataTable)
        row = table.cursor_row
        return self._tracks[row] if 0 <= row < len(self._tracks) else None

    def refresh_queue(self) -> None:
        table = self.query_one("#queue", DataTable)
        table.clear()
        for track in self.queue.items():
            table.add_row(track.title, track.artist)

    @on(DataTable.RowSelected, "#library")
    async def play_selected(self) -> None:
        if not self.session:
            self.notify(
                "mpv is not available; run playquick doctor --install-mpv",
                severity="warning",
            )
            return
        row = self.query_one("#library", DataTable).cursor_row
        if 0 <= row < len(self._tracks):
            await self.session.play_from(self._tracks, row)
            self.query_one(PlayerBar).state = self.controller.state  # type: ignore[union-attr]
            self.refresh_queue()

    @on(ListView.Selected, "#sources")
    def source_selected(self, event: ListView.Selected) -> None:
        source_id = event.item.id
        if source_id == "source-favorites":
            self.load_tracks(self.repository.favorites())
        elif source_id == "source-history":
            self.load_tracks(self.repository.history())
        elif source_id == "source-albums":
            self.load_tracks(self.repository.tracks(order_by="album"))
        elif source_id == "source-artists":
            self.load_tracks(self.repository.tracks(order_by="artist"))
        elif source_id == "source-genres":
            self.load_tracks(self.repository.tracks(order_by="genre"))
        elif source_id == "source-folders":
            self.load_tracks(self.repository.tracks(order_by="path"))
        elif source_id == "source-playlists":
            self.notify("Playlist editor will appear after selecting or creating a playlist")
        elif source_id == "source-spotify":
            self.action_spotify()
        else:
            self.load_tracks(self.repository.tracks())

    @on(Input.Changed, "#search")
    def filter_tracks(self, event: Input.Changed) -> None:
        tracks = self.repository.search(event.value) if event.value else self.repository.tracks()
        self.load_tracks(tracks)

    @on(Input.Submitted, "#search")
    def finish_search(self) -> None:
        search = self.query_one("#search", Input)
        search.remove_class("visible")
        self.query_one("#library", DataTable).focus()

    def action_search(self) -> None:
        search = self.query_one("#search", Input)
        search.add_class("visible")
        search.focus()

    async def action_toggle_pause(self) -> None:
        if self.session:
            await self.session.toggle_pause()
            self.query_one(PlayerBar).state = self.session.controller.state

    def action_queue_append(self) -> None:
        if track := self.selected_track():
            self.queue.append(track)
            self.refresh_queue()
            self.notify(f"Queued {track.title}")

    def action_queue_next(self) -> None:
        if track := self.selected_track():
            self.queue.play_next(track)
            self.refresh_queue()
            self.notify(f"Playing next: {track.title}")

    async def action_next_track(self) -> None:
        if self.session:
            await self.session.next()
            self.refresh_queue()

    async def action_previous_track(self) -> None:
        if self.controller:
            await self.controller.previous()

    async def action_seek(self, seconds: int) -> None:
        if self.controller:
            await self.controller.seek(seconds)

    def action_undo(self) -> None:
        if self.queue.undo():
            self.refresh_queue()
            self.notify("Queue edit undone")

    def action_queue_delete(self) -> None:
        table = self.query_one("#queue", DataTable)
        if self.focused is table and 0 <= table.cursor_row < len(self.queue.explicit):
            track = self.queue.remove(table.cursor_row)
            self.refresh_queue()
            self.notify(f"Removed {track.title}; press u to undo")

    def action_queue_move(self, change: int) -> None:
        table = self.query_one("#queue", DataTable)
        source = table.cursor_row
        target = source + change
        if self.focused is table and 0 <= source < len(self.queue.explicit) and target >= 0:
            self.queue.move(source, target)
            self.refresh_queue()
            table.move_cursor(row=max(0, min(target, len(self.queue.explicit) - 1)))

    def action_favorite(self) -> None:
        if track := self.selected_track():
            self.repository.set_favorite(track.id, True)
            self.notify(f"Favorited {track.title}")

    def action_help(self) -> None:
        self.push_screen(HelpScreen())

    def action_spotify(self) -> None:
        client_id = self.config.spotify_client_id
        if not client_id:
            self.notify("Set your Spotify Client ID in Settings first", severity="warning")
            self.action_settings()
            return
        scopes = BASE_SCOPES + (
            LIBRARY_SCOPES if self.config.spotify_extended_library else ()
        )
        auth = SpotifyAuth(client_id, scopes)
        controller = SpotifyRemoteController(SpotifyClient(auth))
        self.push_screen(
            SpotifyScreen(controller, extended=self.config.spotify_extended_library)
        )

    def action_settings(self) -> None:
        self.push_screen(SettingsScreen(self.config), self._settings_result)

    def _settings_result(self, config: AppConfig | None) -> None:
        if config is None:
            return
        self.config = config
        self.config_store.save(config)
        self.dark = config.theme != "light"
        self.notify("Settings saved")
        if config.music_dirs:
            self.run_worker(self._scan_configured(), name="library-scan", exclusive=True)

    async def action_volume(self, change: int) -> None:
        if self.controller:
            await self.controller.set_volume(self.controller.state.volume + change)
            self.query_one(PlayerBar).state = self.controller.state

    async def action_mute(self) -> None:
        if self.controller:
            await self.controller.set_volume(0)
            self.query_one(PlayerBar).state = self.controller.state

    async def action_shuffle(self) -> None:
        if self.controller:
            await self.controller.set_shuffle(not self.controller.state.shuffle)

    async def action_repeat(self) -> None:
        if not self.controller:
            return
        current = self.controller.state.repeat
        target = {
            RepeatMode.OFF: RepeatMode.ALL,
            RepeatMode.ALL: RepeatMode.ONE,
            RepeatMode.ONE: RepeatMode.OFF,
        }[current]
        await self.controller.set_repeat(target)

    def action_cursor_down(self) -> None:
        if isinstance(self.focused, DataTable):
            self.focused.action_cursor_down()

    def action_cursor_up(self) -> None:
        if isinstance(self.focused, DataTable):
            self.focused.action_cursor_up()

    async def action_quit_app(self) -> None:
        if self.session:
            await self.session.close()
        self.exit()
