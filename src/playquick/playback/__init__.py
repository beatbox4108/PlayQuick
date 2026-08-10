"""Playback controllers."""

from playquick.playback.base import PlaybackController
from playquick.playback.mpv import MpvController

__all__ = ["MpvController", "PlaybackController"]

