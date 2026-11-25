from datetime import datetime
from pathlib import Path
import json
import sys
from c_package.c_maze import get_maze

PROJECT_ROOT = Path(__file__).resolve().parent
RUNS_DIR = PROJECT_ROOT / "runs"

if __name__ == "__main__": #Example run command for width 25, height 29, and difficulty 7: python3 main.py 25 29 7
    W, H = int(sys.argv[1]), int(sys.argv[2]) # Width and height must be odd
    difficulty = int(sys.argv[3]) # Integer from 0-10; 0 has smallest possible # of walls, 10 guarantees exactly one solution

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_name = f"maze_{W}x{H}_d{difficulty}_{timestamp}"
    run_dir = RUNS_DIR / run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    
    maze = get_maze(W, H, difficulty)

    maze_file = run_dir / "maze.json"
    with open(maze_file, "w") as f:
        json.dump({"w": maze.width, "h": maze.height, "difficulty": difficulty, "data": list(maze._packed)}, f)

    # Record this directory as the latest run for Benchmark.py
    (RUNS_DIR / "latest.txt").write_text(str(run_dir))

    print(f"Generated maze in: {run_dir}")