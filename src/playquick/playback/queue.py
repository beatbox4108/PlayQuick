from __future__ import annotations

from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass

from playquick.models import Track
from playquick.storage.repository import LibraryRepository


@dataclass(slots=True)
class QueueSnapshot:
    explicit: list[Track]
    context: list[Track]


class PlaybackQueue:
    """A persistent explicit queue followed by an ephemeral browsing context."""

    def __init__(self, repository: LibraryRepository) -> None:
        self.repository = repository
        self.explicit: deque[Track] = deque(item.track for item in repository.queue())
        self.context: deque[Track] = deque()
        self._undo: list[QueueSnapshot] = []

    def _snapshot(self) -> None:
        self._undo.append(QueueSnapshot(list(self.explicit), list(self.context)))
        self._undo = self._undo[-20:]

    def _persist(self) -> None:
        self.repository.replace_queue([track.id for track in self.explicit])

    def set_context(self, tracks: Sequence[Track]) -> None:
        self.context = deque(tracks)

    def append(self, track: Track) -> None:
        self._snapshot()
        self.explicit.append(track)
        self._persist()

    def play_next(self, track: Track) -> None:
        self._snapshot()
        self.explicit.appendleft(track)
        self._persist()

    def pop_next(self) -> Track | None:
        if self.explicit:
            track = self.explicit.popleft()
            self._persist()
            return track
        return self.context.popleft() if self.context else None

    def remove(self, index: int) -> Track:
        self._snapshot()
        values = list(self.explicit)
        track = values.pop(index)
        self.explicit = deque(values)
        self._persist()
        return track

    def move(self, source: int, target: int) -> None:
        self._snapshot()
        values = list(self.explicit)
        track = values.pop(source)
        values.insert(max(0, min(target, len(values))), track)
        self.explicit = deque(values)
        self._persist()

    def clear(self) -> None:
        self._snapshot()
        self.explicit.clear()
        self.context.clear()
        self._persist()

    def undo(self) -> bool:
        if not self._undo:
            return False
        snapshot = self._undo.pop()
        self.explicit = deque(snapshot.explicit)
        self.context = deque(snapshot.context)
        self._persist()
        return True

    def items(self) -> list[Track]:
        return [*self.explicit, *self.context]

