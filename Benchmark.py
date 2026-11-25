import importlib.util
import sys
import time
from pathlib import Path
from c_package.c_maze import BitMaze, SolverResult

PROJECT_ROOT = Path(__file__).resolve().parent
SOLVERS_DIR = PROJECT_ROOT / "Solvers"
RUNS_DIR = PROJECT_ROOT / "runs"
CHUNK_SIZE = 50_000


def resolve_run_dir() -> Path:
    """Uses the CLI argument if provided, otherwise falls back to runs/latest.txt."""
    if len(sys.argv) > 1:
        return Path(sys.argv[1]).resolve()

    latest_ptr = RUNS_DIR / "latest.txt"
    if latest_ptr.exists():
        return Path(latest_ptr.read_text().strip())

    print("Error: No run directory specified and runs/latest.txt not found. Run main.py first.")
    sys.exit(1)


def load_solver_module(filename: str):
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
    run_dir = resolve_run_dir()
    maze_file = run_dir / "maze.json"
    results_dir = run_dir / "results"

    if not maze_file.exists():
        print(f"Error: {maze_file} not found.")
        sys.exit(1)

    maze = BitMaze.from_json(maze_file)

    solvers = [
        ("Breadth-First Search (BFS)",      "Breadth-first-search.py",           "solve_bfs",        "bfs"),
        ("Depth-First Search (DFS)",        "Depth-first-search.py",             "solve_dfs",        "dfs"),
        ("Left-Wall Follower",              "Left-wall-follow.py",               "solve_left_wall",  "left_wall"),
        ("Right-Wall Follower",             "Right-wall-follow.py",              "solve_right_wall", "right_wall"),
        ("Lobotomized Fruit Fly (Shadow)",  "Labotomized-fruit-fly-Shadow.py", "solve_fruitfly",   "fruitfly"),
    ]

    results = []
    print(f"Run directory: {run_dir}")
    print(f"Running {len(solvers)} solvers on {maze.width}x{maze.height} maze...\n")

    for idx, (label, filename, func_name, subdir) in enumerate(solvers, start=1):
        try:
            mod = load_solver_module(filename)
            solve_fn = getattr(mod, func_name)

            solver_out_dir = results_dir / subdir

            start_time = time.perf_counter()
            solver_res: SolverResult = solve_fn(
                maze,
                output_dir=solver_out_dir,
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
            print_solved_maze(maze, solver_res)
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