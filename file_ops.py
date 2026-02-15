"""File move operations with undo support."""

import shutil
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MoveRecord:
    original: Path
    destination: Path


@dataclass
class MoveResult:
    success: list[MoveRecord] = field(default_factory=list)
    skipped: list[tuple[Path, str]] = field(default_factory=list)


class FileOps:
    """Manages file moves and maintains an undo stack."""

    def __init__(self) -> None:
        self._undo_stack: list[list[MoveRecord]] = []

    def move_files(
        self,
        files: list[tuple[Path, Path]],
        on_conflict: str = "rename",
    ) -> MoveResult:
        """Move a batch of files. Each item is (source, dest_dir).

        on_conflict: 'rename' adds (1), (2), etc.  |  'skip' leaves it  |  'overwrite' replaces.
        Returns a MoveResult. The batch is added to the undo stack.
        """
        result = MoveResult()
        batch: list[MoveRecord] = []

        for src, dest_dir in files:
            if not src.exists():
                result.skipped.append((src, "File no longer exists"))
                continue

            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / src.name

            if dest.exists():
                if on_conflict == "skip":
                    result.skipped.append((src, "File already exists at destination"))
                    continue
                elif on_conflict == "rename":
                    dest = _unique_name(dest)
                elif on_conflict == "overwrite":
                    dest.unlink()

            shutil.move(str(src), str(dest))
            record = MoveRecord(original=src, destination=dest)
            batch.append(record)
            result.success.append(record)

        if batch:
            self._undo_stack.append(batch)

        return result

    @property
    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    def undo_last(self) -> list[MoveRecord]:
        """Undo the most recent batch move. Returns the records that were undone."""
        if not self._undo_stack:
            return []

        batch = self._undo_stack.pop()
        undone: list[MoveRecord] = []

        for record in batch:
            if record.destination.exists():
                record.original.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(record.destination), str(record.original))
                undone.append(record)

        return undone


def _unique_name(path: Path) -> Path:
    """Generate a unique filename by appending (1), (2), etc."""
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    counter = 1
    while True:
        candidate = parent / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1
