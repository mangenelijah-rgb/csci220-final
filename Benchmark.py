import importlib.util
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SOLVERS_DIR = PROJECT_ROOT / "Solvers"
MAZE_FILE = PROJECT_ROOT / "maze.json"

def load_solver_module(filename: str):
    """Dynamically imports solver files even when filenames contain hyphens or parentheses."""
    file_path = SOLVERS_DIR / filename
    if not file_path.exists():
        raise FileNotFoundError(f"Could not find {file_path}")
    spec = importlib.util.spec_from_file_location(filename[:-3], file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

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
        print("Error: maze.json not found. Run 'python3 main.py' first.")
        sys.exit(1)

    with open(MAZE_FILE, "r") as f:
        maze = json.load(f)

    solvers = [
        ("Breadth-First Search (BFS)",      "Breadth-first-search.py",           "solve_bfs"),
        ("Depth-First Search (DFS)",        "Depth-first-search.py",             "solve_dfs"),
        ("Left-Wall Follower",              "Left-wall-follow.py",               "solve_left_wall"),
        ("Right-Wall Follower",             "Right-wall-follow.py",              "solve_right_wall"),
        ("Lobotomized Fruit Fly (Shadow)",  "Labotomized-fruit-fly-(Shadow).py", "solve_fruitfly"),
    ]

    results = []

    print(f"Running {len(solvers)} solvers on {len(maze[0])}x{len(maze)} maze...\n")

    # 1. Run each solver in order and display its visual path + operation count
    for idx, (label, filename, func_name) in enumerate(solvers, start=1):
        try:
            mod = load_solver_module(filename)
            solve_fn = getattr(mod, func_name)

            start_time = time.perf_counter()
            path, operations = solve_fn(maze)
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            steps = len(path) - 1 if path else float("inf")
            results.append({
                "name": label,
                "steps": steps,
                "operations": operations,
                "time_ms": elapsed_ms,
            })

            print("=" * 55)
            print(f"{idx}. {label}")
            print("=" * 55)
            print_solved_maze(maze, path)
            print(f"\nSteps taken: {steps} | Total operations: {operations} | Time: {elapsed_ms:.3f} ms\n")

        except Exception as e:
            print(f"[Warning] Skipped {label}: {e}\n")

    # 2. Sort and display the final ranked list
    results.sort(key=lambda r: (r["steps"], r["operations"]))

    print("=" * 74)
    print(f"FINAL RANKED LEADERBOARD ({len(maze[0])}x{len(maze)} Maze)")
    print("=" * 74)
    header = f"{'Rank':<6} {'Algorithm':<32} {'Steps':<10} {'Operations':<14} {'Time (ms)':<10}"
    print(header)
    print("-" * len(header))

    for rank, r in enumerate(results, start=1):
        print(
            f"#{rank:<5} {r['name']:<32} {r['steps']:<10} "
            f"{r['operations']:<14} {r['time_ms']:.3f}"
        )
