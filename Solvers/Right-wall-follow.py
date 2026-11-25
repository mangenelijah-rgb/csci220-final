import json
import sys
from pathlib import Path
from c_package.c_maze import BitMaze
from c_package.c_maze import SolverResult

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAZE_FILE = PROJECT_ROOT / "maze.json"

# Directions ordered clockwise: 0=North, 1=East, 2=South, 3=West
DIRS = [(0, -1), (1, 0), (0, 1), (-1, 0)]

def get_initial_facing(start: tuple[int, int], width: int, height: int) -> int:
    sx, sy = start
    if sy == 0:
        return 2  # Top wall -> face South
    if sx == width - 1:
        return 3  # Right wall -> face West
    if sy == height - 1:
        return 0  # Bottom wall -> face North
    return 1      # Left wall -> face East

def solve_right_wall(
    maze: BitMaze,
    output_dir: str | Path = PROJECT_ROOT / "results",
    chunk_size: int = 50_000,
) -> SolverResult:
    start = maze.start
    height = len(maze)
    width = len(maze[0])
    end = maze.end

    with SolverResult(
        algorithm="Right-Wall Follower",
        width=width,
        height=height,
        output_dir=output_dir,
        prefix="right_wall",
        chunk_size=chunk_size,
    ) as result:
        x, y = start
        facing = get_initial_facing(start, width, height)
        path = [(x, y)]
        result.record_search(x, y)

        while True:
            result.operations += 1
            if (x, y) == end:
                result.set_solution_path(path)
                return result

            # Check directions: Right (+1), Straight (0), Left (-1), Back (+2)
            for turn in (1, 0, -1, 2):
                result.operations += 1
                next_dir = (facing + turn) % 4
                dx, dy = DIRS[next_dir]
                nx, ny = x + dx, y + dy

                if 0 <= nx < width and 0 <= ny < height and maze[ny][nx] != 1:
                    x, y = nx, ny
                    facing = next_dir
                    path.append((x, y))
                    result.record_search(x, y)
                    break


def print_solved_maze(maze: BitMaze, result: SolverResult):
    symbols = {0: "  ", 1: "##", 2: "S ", 3: "E "}

    for y, row in enumerate(maze):
        line = []
        for x, cell in enumerate(row):
            if result.is_on_path(x, y) and cell == 0:
                line.append("• ")
            else:
                line.append(symbols[cell])
        print("".join(line))


if __name__ == "__main__":
    if not MAZE_FILE.exists():
        print("Error: maze.json not found. Run main.py first to generate a maze.")
        sys.exit(1)

    maze = BitMaze.from_json(MAZE_FILE)
    result = solve_right_wall(maze)

    print("Algorithm: Right-Wall Follower\n")
    print_solved_maze(maze, result)
    print(f"\nSteps taken: {result.steps}")
    print(f"Total operations: {result.operations}")