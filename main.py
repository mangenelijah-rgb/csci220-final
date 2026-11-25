from datetime import datetime
from pathlib import Path
import json
import sys
import random
from c_package.c_maze import get_maze

PROJECT_ROOT = Path(__file__).resolve().parent
RUNS_DIR = PROJECT_ROOT / "runs"


def pick_random_start_end(maze) -> tuple[tuple[int, int], tuple[int, int]]:
    w, h = maze.width, maze.height
    candidates = set()

    # Top (y=0) and bottom (y=h-1) outer walls
    for x in range(1, w - 1):
        if maze[1][x] == 0:
            candidates.add((x, 0))
        if maze[h - 2][x] == 0:
            candidates.add((x, h - 1))

    # Left (x=0) and right (x=w-1) outer walls
    for y in range(1, h - 1):
        if maze[y][1] == 0:
            candidates.add((0, y))
        if maze[y][w - 2] == 0:
            candidates.add((w - 1, y))

    if len(candidates) < 2:
        raise ValueError("Not enough viable outer wall openings found.")

    start, end = random.sample(list(candidates), 2)
    return start, end


if __name__ == "__main__":
    W, H = int(sys.argv[1]), int(sys.argv[2])
    difficulty = int(sys.argv[3])

    maze = get_maze(W, H, difficulty)

    start, end = pick_random_start_end(maze)
    maze.set_path(*start)
    maze.set_path(*end)
    maze.start = start
    maze.end = end

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_name = f"maze_{W}x{H}_d{difficulty}_{timestamp}"
    run_dir = RUNS_DIR / run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    maze_file = run_dir / "maze.json"
    with open(maze_file, "w") as f:
        json.dump(
            {
                "w": maze.width,
                "h": maze.height,
                "difficulty": difficulty,
                "start": list(start),
                "end": list(end),
                "data": list(maze._packed),
            },
            f,
        )

    (RUNS_DIR / "latest.txt").write_text(str(run_dir))

    print(f"Generated maze in: {run_dir}")
    print(f"Start: {start} | End: {end}")