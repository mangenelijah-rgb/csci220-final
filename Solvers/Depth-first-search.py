import json
import sys
from pathlib import Path
from c_package.c_maze import BitMaze

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MAZE_FILE = PROJECT_ROOT / "maze.json"

# Directions: North, East, South, West
DIRS = [(0, -1), (1, 0), (0, 1), (-1, 0)]

def solve_dfs(maze: list[list[int]]):
    start = (0,1)
    height = len(maze)
    width = len(maze[0])
    end = (width -1, height - 2)

    stack = [start]
    came_from = {start: None}
    operations = 0

    while stack:
        x, y = stack.pop()
        operations += 1  # Count popping/visiting a cell from the stack

        if (x,y) == end:
            # Reconstruct the discovered path from End back to Start
            path = []
            curr = (x, y)
            while curr is not None:
                path.append(curr)
                curr = came_from[curr]
            path.reverse()
            return path, operations

        for dx, dy in DIRS:
            operations += 1  # Count each neighbor inspection as an operation
            nx, ny = x + dx, y + dy

            if 0 <= nx < width and 0 <= ny < height:
                if maze[ny][nx] != 1 and (nx, ny) not in came_from:
                    came_from[(nx, ny)] = (x, y)
                    stack.append((nx, ny))

    return [], operations

def print_solved_maze(maze: list[list[int]], path: list[tuple[int, int]]):
    path_set = set(path)
    symbols = {0: "  ", 1: "##"}

    for y, row in enumerate(maze):
        line = []
        for x, cell in enumerate(row):
            if (x, y) in path_set and cell == 0:
                line.append("• ")
            else:
                line.append(symbols[cell])
        print("".join(line))

if __name__ == "__main__":
    if not MAZE_FILE.exists():
        print("Error: maze.json not found. Run main.py first to generate a maze.")
        sys.exit(1)

    maze = BitMaze.from_json(MAZE_FILE)

    path, operations = solve_dfs(maze)

    print("Algorithm: Depth-First Search (DFS)\n")
    print_solved_maze(maze, path)

    # Output stats and steps taken after the solved maze
    print(f"\nSteps taken: {len(path) - 1}")
    print(f"Total operations: {operations}")
