import json
import sys
from pathlib import Path
from c_package.c_maze import BitMaze
from c_package.c_maze import SolverResult

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAZE_FILE = PROJECT_ROOT / "maze.json"

# Directions: North, East, South, West
DIRS = [(0, -1), (1, 0), (0, 1), (-1, 0)]


def solve_dfs(
    maze: BitMaze,
    output_dir: str | Path = PROJECT_ROOT / "results",
    chunk_size: int = 50_000,
) -> SolverResult:
    start = maze.start
    height = len(maze)
    width = len(maze[0])
    end = maze.end

    with SolverResult(
        algorithm="Depth-First Search (DFS)",
        width=width,
        height=height,
        output_dir=output_dir,
        prefix="dfs",
        chunk_size=chunk_size,
    ) as result:
        stack = [start]
        came_from = {start: None}

        while stack:
            x, y = stack.pop()
            result.operations += 1
            result.record_search(x, y)

            if (x, y) == end:
                path = []
                curr = (x, y)
                while curr is not None:
                    path.append(curr)
                    curr = came_from[curr]
                path.reverse()

                result.set_solution_path(path)
                return result

            for dx, dy in DIRS:
                result.operations += 1
                nx, ny = x + dx, y + dy

                if 0 <= nx < width and 0 <= ny < height:
                    if maze[ny][nx] != 1 and (nx, ny) not in came_from:
                        came_from[(nx, ny)] = (x, y)
                        stack.append((nx, ny))

        return result


def print_solved_maze(maze: BitMaze, result: SolverResult):
    symbols = {0: "  ", 1: "##"}

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
    result = solve_dfs(maze)

    print("Algorithm: Depth-First Search (DFS)\n")
    print_solved_maze(maze, result)
    print(f"\nSteps taken: {result.steps}")
    print(f"Total operations: {result.operations}")