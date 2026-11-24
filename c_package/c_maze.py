import ctypes
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LIB_NAME = "maze.dll" if os.name == "nt" else "maze.so"
LIB_PATH = PROJECT_ROOT / "build" / LIB_NAME

if not LIB_PATH.exists():
    raise FileNotFoundError(f"Compiled library not found at {LIB_PATH}. Run 'make' first.")

_lib = ctypes.CDLL(str(LIB_PATH))

_lib.generate_maze.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
_lib.generate_maze.restype = ctypes.POINTER(ctypes.c_uint8)

_lib.free_maze.argtypes = [ctypes.POINTER(ctypes.c_uint8)]
_lib.free_maze.restype = None

def get_maze(width: int, height: int, difficulty: int) -> list[list[int]]:
    maze = _lib.generate_maze(width, height, difficulty)
    if not maze:
        raise MemoryError("Failed to allocate memory for maze")
    try:
        data = maze[: width * height]
        return [data[y * width : (y + 1) * width] for y in range(height)]
    finally:
        _lib.free_maze(maze)
