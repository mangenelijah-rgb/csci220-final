import array
import ctypes
import os
import json
from pathlib import Path
from typing import Iterator

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LIB_NAME = "maze.dll" if os.name == "nt" else "maze.so"
LIB_PATH = PROJECT_ROOT / "build" / LIB_NAME

if not LIB_PATH.exists():
    raise FileNotFoundError(f"Compiled library not found at {LIB_PATH}. Run 'make' first.")

_lib = ctypes.CDLL(str(LIB_PATH))

_lib.generate_maze.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
_lib.generate_maze.restype = ctypes.POINTER(ctypes.c_uint32)

_lib.free_maze.argtypes = [ctypes.POINTER(ctypes.c_uint32)]
_lib.free_maze.restype = None


class _MazeRow:
    """Lightweight view of a single row that extracts bits on demand."""
    __slots__ = ("_packed", "_offset", "_width")

    def __init__(self, packed: array.array, offset: int, width: int):
        self._packed = packed
        self._offset = offset
        self._width = width

    def __getitem__(self, x: int) -> int:
        if x < 0:
            x += self._width
        if not (0 <= x < self._width):
            raise IndexError("Column index out of range")
        idx = self._offset + x
        return (self._packed[idx >> 5] >> (idx & 31)) & 1

    def __len__(self) -> int:
        return self._width

    def __iter__(self):
        for x in range(self._width):
            idx = self._offset + x
            yield (self._packed[idx >> 5] >> (idx & 31)) & 1


class BitMaze:
    """Memory-efficient bit-packed 2D maze supporting maze[y][x] access."""
    __slots__ = ("width", "height", "_packed", "start", "end")

    def __init__(
        self,
        width: int,
        height: int,
        packed: array.array,
        start: tuple[int, int] | None = None,
        end: tuple[int, int] | None = None,
    ):
        self.width = width
        self.height = height
        self._packed = packed
        self.start = start if start is not None else (0, 1)
        self.end = end if end is not None else (width - 1, height - 2)

    def set_path(self, x: int, y: int) -> None:
        """Sets the bit at (x, y) to 0 (open path)."""
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise IndexError("Coordinates out of bounds")
        idx = y * self.width + x
        self._packed[idx >> 5] &= ~(1 << (idx & 31))

    @classmethod
    def from_json(cls, filepath: str | Path) -> "BitMaze":
        """Load a packed maze JSON file directly into a BitMaze object."""
        with open(filepath, "r") as f:
            payload = json.load(f)
        packed = array.array("I", payload["data"])
        default_end = (payload["w"] - 1, payload["h"] - 2)
        start = tuple(payload["start"]) if "start" in payload else (0, 1)
        end = tuple(payload["end"]) if "end" in payload else default_end
        return cls(payload["w"], payload["h"], packed, start=start, end=end)

    def __getitem__(self, y: int) -> _MazeRow:
        if y < 0:
            y += self.height
        if not (0 <= y < self.height):
            raise IndexError("Row index out of range")
        return _MazeRow(self._packed, y * self.width, self.width)

    def __len__(self) -> int:
        return self.height

    def __iter__(self):
        for y in range(self.height):
            yield self[y]

    def to_list(self) -> list[list[int]]:
        """Unpack into a standard 2D list (useful for json.dump)."""
        return [list(row) for row in self]


def get_maze(width: int, height: int, difficulty: int) -> BitMaze:
    maze_ptr = _lib.generate_maze(width, height, difficulty)
    if not maze_ptr:
        raise MemoryError("Failed to allocate memory for maze")
    try:
        total_cells = width * height
        num_ints = (total_cells + 31) // 32
        packed = array.array("I", maze_ptr[:num_ints])
        return BitMaze(width, height, packed)
    finally:
        _lib.free_maze(maze_ptr)

class SolverResult:
    """
    Streams searched coordinates to chunked JSON files as the solver runs to keep RAM flat,
    and stores the final solution path as a bit-packed 32-bit integer array.
    """
    __slots__ = (
        "algorithm",
        "width",
        "height",
        "operations",
        "steps",
        "path_packed",
        "output_dir",
        "prefix",
        "chunk_size",
        "searched_count",
        "_buffer",
        "_chunk_files",
        "_finalized",
    )

    def __init__(
        self,
        algorithm: str,
        width: int,
        height: int,
        output_dir: str | Path,
        prefix: str,
        chunk_size: int = 50_000,
        path_packed: array.array | None = None,
    ):
        self.algorithm = algorithm
        self.width = width
        self.height = height
        self.operations = 0
        self.steps = 0
        self.searched_count = 0

        self.output_dir = Path(output_dir)
        self.prefix = prefix
        self.chunk_size = chunk_size

        self._buffer: list[tuple[int, int]] = []
        self._chunk_files: list[str] = []
        self._finalized = False

        if path_packed is not None:
            self.path_packed = path_packed
        else:
            total_cells = width * height
            num_ints = (total_cells + 31) // 32
            self.path_packed = array.array("I", [0] * num_ints)

    def __enter__(self) -> "SolverResult":
        self.output_dir.mkdir(parents=True, exist_ok=True)
        # Clean up any leftover chunk files from a previous run with the same prefix
        for old_file in self.output_dir.glob(f"{self.prefix}_searched_*.json"):
            old_file.unlink()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.finalize()

    def record_search(self, x: int, y: int) -> None:
        """Appends a visited coordinate to the small RAM buffer and flushes to disk when full."""
        self._buffer.append((x, y))
        self.searched_count += 1
        if len(self._buffer) >= self.chunk_size:
            self._flush_buffer()

    def _flush_buffer(self) -> None:
        """Writes the current buffer to the next numbered JSON file and clears RAM."""
        if not self._buffer:
            return
        chunk_idx = len(self._chunk_files)
        chunk_filename = f"{self.prefix}_searched_{chunk_idx}.json"
        with open(self.output_dir / chunk_filename, "w") as f:
            json.dump(self._buffer, f, separators=(",", ":"))
        self._chunk_files.append(chunk_filename)
        self._buffer.clear()  # Frees the buffer memory immediately

    def set_solution_path(self, path: list[tuple[int, int]]) -> None:
        """Packs the final solution coordinates into the bitfield (1 = on path, 0 = off path)."""
        self.steps = len(path) - 1 if path else 0
        for x, y in path:
            if not (0 <= x < self.width and 0 <= y < self.height):
                raise IndexError(f"Coordinates ({x}, {y}) out of bounds")
            idx = y * self.width + x
            self.path_packed[idx >> 5] |= (1 << (idx & 31))

    def is_on_path(self, x: int, y: int) -> int:
        """Returns 1 if (x, y) is on the final solution path, 0 otherwise."""
        if not (0 <= x < self.width and 0 <= y < self.height):
            return 0
        idx = y * self.width + x
        return (self.path_packed[idx >> 5] >> (idx & 31)) & 1

    def finalize(self) -> Path:
        """Flushes any remaining buffered coordinates and writes the metadata JSON."""
        if self._finalized:
            return self.output_dir / f"{self.prefix}_meta.json"

        self._flush_buffer()

        meta = {
            "algorithm": self.algorithm,
            "w": self.width,
            "h": self.height,
            "steps": self.steps,
            "operations": self.operations,
            "searched_count": self.searched_count,
            "path_packed": list(self.path_packed),
            "searched_chunks": self._chunk_files,
        }

        meta_file = self.output_dir / f"{self.prefix}_meta.json"
        with open(meta_file, "w") as f:
            json.dump(meta, f, separators=(",", ":"))

        self._finalized = True
        return meta_file

    def iter_searched(self) -> Iterator[tuple[int, int]]:
        """
        Streams coordinates back from disk one chunk at a time so replay/visualization
        also never loads the entire search history into RAM at once.
        """
        for chunk_filename in self._chunk_files:
            with open(self.output_dir / chunk_filename, "r") as f:
                for pt in json.load(f):
                    yield (pt[0], pt[1])
        # Also yield anything still un-flushed if called mid-run
        for pt in self._buffer:
            yield pt

    @classmethod
    def load_from_json(cls, meta_filepath: str | Path) -> "SolverResult":
        """Loads the metadata and bit-packed solution without loading all search chunks into RAM."""
        meta_path = Path(meta_filepath)
        with open(meta_path, "r") as f:
            meta = json.load(f)

        obj = cls(
            algorithm=meta["algorithm"],
            width=meta["w"],
            height=meta["h"],
            output_dir=meta_path.parent,
            prefix=meta_path.name.removesuffix("_meta.json"),
            path_packed=array.array("I", meta["path_packed"]),
        )
        obj.operations = meta["operations"]
        obj.steps = meta["steps"]
        obj.searched_count = meta["searched_count"]
        obj._chunk_files = meta["searched_chunks"]
        obj._finalized = True
        return obj