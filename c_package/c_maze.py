import array
import ctypes
import os
import json
from pathlib import Path

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
    __slots__ = ("width", "height", "_packed")

    def __init__(self, width: int, height: int, packed: array.array):
        self.width = width
        self.height = height
        self._packed = packed

    @classmethod
    def from_json(cls, filepath: str | Path) -> "BitMaze":
        """Load a packed maze JSON file directly into a BitMaze object."""
        with open(filepath, "r") as f:
            payload = json.load(f)
        packed = array.array("I", payload["data"])
        return cls(payload["w"], payload["h"], packed)

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