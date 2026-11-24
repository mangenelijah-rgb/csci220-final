import importlib.util
import sys
import time
from pathlib import Path
from c_package.c_maze import BitMaze, SolverResult

PROJECT_ROOT = Path(__file__).resolve().parent
SOLVERS_DIR = PROJECT_ROOT / "Solvers"
MAZE_FILE = PROJECT_ROOT / "maze.json"
RESULTS_DIR = PROJECT_ROOT / "results"
CHUNK_SIZE = 50_000


def load_solver_module(filename: str):
    """Dynamically imports solver files even when filenames contain hyphens or parentheses."""
    file_path = SOLVERS_DIR / filename
    if not file_path.exists():
        raise FileNotFoundError(f"Could not find {file_path}")
    spec = importlib.util.spec_from_file_location(filename[:-3], file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
        print("Error: maze.json not found. Run 'python3 main.py' first.")
        sys.exit(1)

    maze = BitMaze.from_json(MAZE_FILE)

    solvers = [
        ("Breadth-First Search (BFS)",      "Breadth-first-search.py",           "solve_bfs"),
        ("Depth-First Search (DFS)",        "Depth-first-search.py",             "solve_dfs"),
        ("Left-Wall Follower",              "Left-wall-follow.py",               "solve_left_wall"),
        ("Right-Wall Follower",             "Right-wall-follow.py",              "solve_right_wall"),
        ("Lobotomized Fruit Fly (Shadow)",  "Labotomized-fruit-fly-Shadow.py", "solve_fruitfly"),
    ]

    results = []

    print(f"Running {len(solvers)} solvers on {maze.width}x{maze.height} maze...\n")

    for idx, (label, filename, func_name) in enumerate(solvers, start=1):
        try:
            mod = load_solver_module(filename)
            solve_fn = getattr(mod, func_name)

            start_time = time.perf_counter()
            solver_res: SolverResult = solve_fn(
                maze,
                output_dir=RESULTS_DIR,
                chunk_size=CHUNK_SIZE,
            )
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            steps = solver_res.steps if solver_res.steps > 0 else float("inf")
            results.append({
                "name": label,
                "steps": steps,
                "operations": solver_res.operations,
                "searched": solver_res.searched_count,
                "chunks": len(solver_res._chunk_files),
                "time_ms": elapsed_ms,
            })

            print("=" * 65)
            print(f"{idx}. {label}")
            print("=" * 65)
            # print_solved_maze(maze, solver_res)


            #To get each step of the solution:
            #print(f"Search order for {solver_res.algorithm}:")
            #for step, (x, y) in enumerate(solver_res.iter_searched()):
            #    print(f"Step {step}: ({x}, {y})")



            print(
                f"\nSteps: {steps} | Operations: {solver_res.operations} | "
                f"Searched: {solver_res.searched_count} ({len(solver_res._chunk_files)} JSON chunks) | "
                f"Time: {elapsed_ms:.3f} ms\n"
            )

        except Exception as e:
            print(f"[Warning] Skipped {label}: {e}\n")

    results.sort(key=lambda r: (r["steps"], r["operations"]))

    print("=" * 86)
    print(f"FINAL RANKED LEADERBOARD ({maze.width}x{maze.height} Maze)")
    print("=" * 86)
    header = (
        f"{'Rank':<6} {'Algorithm':<32} {'Steps':<10} "
        f"{'Operations':<14} {'Searched':<12} {'Time (ms)':<10}"
    )
    print(header)
    print("-" * len(header))

    for rank, r in enumerate(results, start=1):
        print(
            f"#{rank:<5} {r['name']:<32} {r['steps']:<10} "
            f"{r['operations']:<14} {r['searched']:<12} {r['time_ms']:.3f}"
        )