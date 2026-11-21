import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAZE_FILE = PROJECT_ROOT / "maze.json"

# Directions ordered clockwise: 0=North, 1=East, 2=South, 3=West
DIRS = [(0, -1), (1, 0), (0, 1), (-1, 0)]

def find_start(maze: list[list[int]]):
    for y, row in enumerate(maze):
        for x, cell in enumerate(row):
            if cell == 2:
                return (x, y)
    return None

def solve_right_wall(maze: list[list[int]]):
    start = find_start(maze)
    height = len(maze)
    width = len(maze[0])

    x, y = start
    facing = 1  # Start facing East (into the maze from left edge)
    path = [(x, y)]
    operations = 0

    while True:
        operations += 1  # Check if current cell is the exit
        if maze[y][x] == 3:
            return path, operations

        # Check directions: Right (+1), Straight (0), Left (-1), Back (+2)
        for turn in (1, 0, -1, 2):
            operations += 1  # Count each neighbor inspection as an operation
            next_dir = (facing + turn) % 4
            dx, dy = DIRS[next_dir]
            nx, ny = x + dx, y + dy

            if 0 <= nx < width and 0 <= ny < height and maze[ny][nx] != 1:
                x, y = nx, ny
                facing = next_dir
                path.append((x, y))
                break

def print_solved_maze(maze: list[list[int]], path: list[tuple[int, int]]):
    path_set = set(path)
    symbols = {0: "  ", 1: "##", 2: "S ", 3: "E "}

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

    with open(MAZE_FILE, "r") as f:
        maze = json.load(f)

    path, operations = solve_right_wall(maze)

    print("Algorithm: Right-Wall Follower\n")
    print_solved_maze(maze, path)

    # Output stats and steps taken after the solved maze
    print(f"\nSteps taken: {len(path) - 1}")
    print(f"Total operations: {operations}")
