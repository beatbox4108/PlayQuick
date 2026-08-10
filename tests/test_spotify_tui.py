from __future__ import annotations

import pytest
from textual.app import App
from textual.widgets import Select

from playquick.spotify.client import SpotifyError
from playquick.spotify.models import SpotifyDevice, SpotifyPlayback, SpotifyTrack
from playquick.tui.spotify import SpotifyScreen


class FakeSpotifyClient:
    def __init__(self) -> None:
        self.next_calls = 0
        self.previous_calls = 0

    async def queue(self) -> list[SpotifyTrack]:
        return []

    async def next(self) -> None:
        self.next_calls += 1

    async def previous(self) -> None:
        self.previous_calls += 1


class FakeSpotifyController:
    def __init__(self) -> None:
        self.client = FakeSpotifyClient()
        self.devices_value = [
            SpotifyDevice("active", "Desktop", "Computer", 50, True),
            SpotifyDevice("other", "Phone", "Smartphone", 50, False),
        ]
        self.state = SpotifyPlayback(False, 1000, None, self.devices_value[0])
        self.transfers: list[str] = []
        self.resume_calls = 0
        self.pause_error: SpotifyError | None = None

    async def devices(self) -> list[SpotifyDevice]:
        return self.devices_value

    async def poll(self) -> SpotifyPlayback:
        return self.state

    async def transfer(self, device_id: str, *, play: bool = False) -> None:
        self.transfers.append(device_id)
        device = next(device for device in self.devices_value if device.id == device_id)
        self.state = SpotifyPlayback(False, 1000, None, device)

    async def resume(self) -> None:
        self.resume_calls += 1
        self.state = SpotifyPlayback(True, 1000, None, self.state.device)

    async def pause(self) -> None:
        if self.pause_error:
            raise self.pause_error

    async def play(self, _track: SpotifyTrack) -> None:
        return None

    async def add_to_queue(self, _track: SpotifyTrack) -> None:
        return None


@pytest.mark.asyncio
async def test_spotify_mount_does_not_transfer_active_device() -> None:
    controller = FakeSpotifyController()
    screen = SpotifyScreen(controller, extended=False)  # type: ignore[arg-type]
    app = App()

    async with app.run_test() as pilot:
        app.push_screen(screen)
        await pilot.pause()

        selector = screen.query_one("#spotify-device", Select)
        assert selector.value == "active"
        assert controller.transfers == []

        selector.value = "other"
        await pilot.pause()

        assert controller.transfers == ["other"]


@pytest.mark.asyncio
async def test_spotify_play_pause_resumes_current_playback() -> None:
    controller = FakeSpotifyController()
    screen = SpotifyScreen(controller, extended=False)  # type: ignore[arg-type]
    app = App()

    async with app.run_test() as pilot:
        app.push_screen(screen)
        await pilot.pause()

        await screen.action_play_pause()

        assert controller.resume_calls == 1
        assert controller.state.playing


@pytest.mark.asyncio
async def test_spotify_command_error_does_not_escape_screen() -> None:
    controller = FakeSpotifyController()
    controller.state = SpotifyPlayback(True, 1000, None, controller.devices_value[0])
    controller.pause_error = SpotifyError(403, "Restriction violated", "UNKNOWN")
    screen = SpotifyScreen(controller, extended=False)  # type: ignore[arg-type]
    app = App()

    async with app.run_test() as pilot:
        app.push_screen(screen)
        await pilot.pause()

        await screen.action_play_pause()
