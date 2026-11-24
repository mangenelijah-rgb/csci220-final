import importlib.util
import json
import math
import sys
import time
import tkinter as tk
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SOLVERS_DIR = PROJECT_ROOT / "Solvers"
MAZE_FILE = PROJECT_ROOT / "maze.json"

MAX_WINDOW_PX = 850
TARGET_ANIMATION_SECONDS = 4.0   # Playback duration per solver


def load_solver_module(filename: str):
    file_path = SOLVERS_DIR / filename
    if not file_path.exists():
        raise FileNotFoundError(f"Could not find {file_path}")
    spec = importlib.util.spec_from_file_location(filename[:-3], file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PostBenchmarkAnimator:
    def __init__(self, maze: list[list[int]], solver_runs: list[dict]):
        self.maze = maze
        self.solver_runs = solver_runs
        self.rows = len(maze)
        self.cols = len(maze[0])

        self.step = max(1, math.ceil(max(self.cols, self.rows) / MAX_WINDOW_PX))
        self.img_w = math.ceil(self.cols / self.step)
        self.img_h = math.ceil(self.rows / self.step)
        self.zoom_factor = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.paused = False

        self.current_idx = 0
        self.current_step_k = 0
        self.after_id = None

        self.root = tk.Tk()
        self.root.title(f"Maze Solver Replay ({self.cols}x{self.rows})")
        self.root.configure(bg="#1e1e1e")

        # Top HUD Bar
        top_frame = tk.Frame(self.root, bg="#1e1e1e")
        top_frame.pack(fill=tk.X, padx=12, pady=6)

        self.status_var = tk.StringVar(value="Preparing replay...")
        tk.Label(
            top_frame,
            textvariable=self.status_var,
            font=("Consolas", 10, "bold"),
            bg="#1e1e1e",
            fg="#ffffff",
        ).pack(side=tk.LEFT)

        btn_style = {
            "font": ("Consolas", 9, "bold"),
            "bg": "#333842",
            "fg": "#ffffff",
            "relief": tk.FLAT,
            "padx": 8,
            "pady": 2,
        }
        tk.Button(top_frame, text="Reset (R)", command=self.reset_zoom, **btn_style).pack(side=tk.RIGHT, padx=(4, 0))
        tk.Button(top_frame, text="Zoom In (+)", command=lambda: self.on_zoom(1.5), **btn_style).pack(side=tk.RIGHT, padx=4)
        tk.Button(top_frame, text="Zoom Out (-)", command=lambda: self.on_zoom(0.67), **btn_style).pack(side=tk.RIGHT, padx=4)
        tk.Button(top_frame, text="Next (N)", command=self.skip_to_next, **btn_style).pack(side=tk.RIGHT, padx=4)
        self.pause_btn = tk.Button(top_frame, text="Pause (Space)", command=self.toggle_pause, **btn_style)
        self.pause_btn.pack(side=tk.RIGHT, padx=4)

        self.canvas = tk.Canvas(self.root, width=self.img_w, height=self.img_h, bg="#111111", highlightthickness=0)
        self.canvas.pack(padx=12, pady=(0, 12))

        # Laptop Controls
        self.root.bind("<space>", lambda e: self.toggle_pause())
        self.root.bind("n", lambda e: self.skip_to_next())
        self.root.bind("N", lambda e: self.skip_to_next())
        for key in ("z", "Z", "<plus>", "<equal>"):
            self.root.bind(key, lambda e: self.on_zoom(1.5))
        for key in ("x", "X", "<minus>"):
            self.root.bind(key, lambda e: self.on_zoom(0.67))
        for key in ("r", "R"):
            self.root.bind(key, lambda e: self.reset_zoom())
        for key, dx, dy in [
            ("<Left>", 60, 0),
            ("<Right>", -60, 0),
            ("<Up>", 0, 60),
            ("<Down>", 0, -60),
            ("a", 60, 0),
            ("d", -60, 0),
            ("w", 0, 60),
            ("s", 0, -60),
        ]:
            self.root.bind(key, lambda e, x=dx, y=dy: self.pan_by(x, y))

        self.canvas.bind("<ButtonPress-1>", self.on_pan_start)
        self.canvas.bind("<B1-Motion>", self.on_pan_move)

        self.build_maze_image()
        self.root.after(200, self.start_next_solver)

    def build_maze_image(self):
        self.base_photo = tk.PhotoImage(width=self.img_w, height=self.img_h)
        palette = {0: "#111111", 1: "#2d323b", 2: "#00e676", 3: "#ff1744"}
        rows_data = []
        for iy in range(self.img_h):
            my = min(self.rows - 1, iy * self.step)
            row = self.maze[my]
            rows_data.append(
                "{" + " ".join(palette[row[min(self.cols - 1, ix * self.step)]] for ix in range(self.img_w)) + "}"
            )
        self.base_photo.put(" ".join(rows_data))
        self.display_photo = self.base_photo
        self.image_id = self.canvas.create_image(0, 0, anchor=tk.NW, image=self.display_photo)

    def toggle_pause(self):
        self.paused = not self.paused
        self.pause_btn.config(text="Resume (Space)" if self.paused else "Pause (Space)")

    def skip_to_next(self):
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        self.current_idx += 1
        self.start_next_solver()

    def on_zoom(self, factor: float):
        new_zoom = max(1.0, min(16.0, self.zoom_factor * factor))
        scale_int = max(1, round(new_zoom))
        if scale_int == int(self.zoom_factor):
            return
        self.zoom_factor = float(scale_int)
        self.display_photo = self.base_photo.zoom(scale_int, scale_int) if scale_int > 1 else self.base_photo
        self.canvas.itemconfig(self.image_id, image=self.display_photo)
        self.redraw_trail()

    def pan_by(self, dx: float, dy: float):
        self.pan_x += dx
        self.pan_y += dy
        self.canvas.coords(self.image_id, self.pan_x, self.pan_y)
        self.canvas.move("trail", dx, dy)
        self.canvas.move("head", dx, dy)

    def on_pan_start(self, event):
        self._drag_last = (event.x, event.y)

    def on_pan_move(self, event):
        dx, dy = event.x - self._drag_last[0], event.y - self._drag_last[1]
        self._drag_last = (event.x, event.y)
        self.pan_by(dx, dy)

    def reset_zoom(self):
        self.zoom_factor = 1.0
        self.pan_x = self.pan_y = 0.0
        self.display_photo = self.base_photo
        self.canvas.itemconfig(self.image_id, image=self.display_photo)
        self.canvas.coords(self.image_id, 0, 0)
        self.redraw_trail()

    def grid_to_screen(self, gx: int, gy: int):
        scale = self.zoom_factor / self.step
        return self.pan_x + gx * scale, self.pan_y + gy * scale

    def redraw_trail(self):
        self.canvas.delete("trail", "head")
        if self.current_idx >= len(self.solver_runs):
            return
        path = self.solver_runs[self.current_idx]["path"]
        if not path:
            return
        end_k = min(len(path) - 1, self.current_step_k)
        if end_k >= 1:
            stride = max(1, end_k // 4500)
            pts = []
            for gx, gy in path[: end_k + 1 : stride]:
                pts.extend(self.grid_to_screen(gx, gy))
            if len(pts) % 2 == 1:
                pts = pts[:-1]
            if len(pts) >= 4:
                self.canvas.create_line(
                    *pts, fill="#00b0ff", width=max(1, int(self.zoom_factor // 2)), tags="trail"
                )
        hx, hy = self.grid_to_screen(*path[end_k])
        r = max(4, int(2 * self.zoom_factor))
        self.canvas.create_oval(hx - r, hy - r, hx + r, hy + r, fill="#ffd600", outline="", tags="head")

    def start_next_solver(self):
        if self.current_idx >= len(self.solver_runs):
            self.status_var.set("ALL REPLAYS FINISHED! Zoom/Pan freely or close window.")
            return

        self.canvas.delete("trail", "head")
        run = self.solver_runs[self.current_idx]
        path = run["path"]

        if not path:
            self.current_idx += 1
            self.after_id = self.root.after(200, self.start_next_solver)
            return

        total_steps = len(path) - 1
        stride = max(1, len(path) // 180)
        delay_ms = max(16, int((TARGET_ANIMATION_SECONDS * 1000) / max(1, len(path) / stride)))
        self.current_step_k = 0
        self.animate_step(run, 0, stride, delay_ms, total_steps)

    def animate_step(self, run: dict, step_idx: int, stride: int, delay_ms: int, total_steps: int):
        if self.paused:
            self.after_id = self.root.after(50, self.animate_step, run, step_idx, stride, delay_ms, total_steps)
            return

        path = run["path"]
        end_k = min(len(path) - 1, step_idx)
        start_k = max(0, step_idx - stride)
        self.current_step_k = end_k

        if end_k > start_k:
            seg = path[start_k : end_k + 1]
            sub_stride = max(1, len(seg) // 250)
            pts = []
            for gx, gy in seg[::sub_stride]:
                pts.extend(self.grid_to_screen(gx, gy))
            if len(pts) % 2 == 1:
                pts = pts[:-1]
            if len(pts) >= 4:
                self.canvas.create_line(
                    *pts, fill="#00b0ff", width=max(1, int(self.zoom_factor // 2)), tags="trail"
                )

        hx, hy = self.grid_to_screen(*path[end_k])
        r = max(4, int(2 * self.zoom_factor))
        self.canvas.delete("head")
        self.canvas.create_oval(hx - r, hy - r, hx + r, hy + r, fill="#ffd600", outline="", tags="head")

        self.status_var.set(
            f"[{self.current_idx + 1}/{len(self.solver_runs)}] {run['name']} | "
            f"Step {end_k:,}/{total_steps:,} | Zoom: {self.zoom_factor:.0f}x"
        )

        if end_k < len(path) - 1:
            next_idx = min(len(path) - 1, step_idx + stride)
            self.after_id = self.root.after(
                delay_ms, self.animate_step, run, next_idx, stride, delay_ms, total_steps
            )
        else:
            self.status_var.set(
                f"[{self.current_idx + 1}/{len(self.solver_runs)}] {run['name']} — DONE! | "
                f"Steps: {total_steps:,} | Ops: {run['operations']:,} | Time: {run['time_ms']:.2f} ms"
            )
            self.current_idx += 1
            self.current_idx += 1
            self.after_id = self.root.after(1200, self.start_next_solver)

    def run(self):
        self.root.mainloop()


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

    # 1. Run and benchmark all algorithms FIRST
    solver_runs = []
    print(f"Benchmarking {len(solvers)} solvers on {len(maze[0])}x{len(maze)} maze...\n")

    for label, filename, func_name in solvers:
        try:
            mod = load_solver_module(filename)
            solve_fn = getattr(mod, func_name)

            t0 = time.perf_counter()
            path, operations = solve_fn(maze)
            elapsed_ms = (time.perf_counter() - t0) * 1000

            steps = len(path) - 1 if path else float("inf")
            solver_runs.append({
                "name": label,
                "path": path,
                "steps": steps,
                "operations": operations,
                "time_ms": elapsed_ms,
            })
            print(f"  ✓ {label:<32} | Steps: {steps:<10,} | Ops: {operations:<13,} | {elapsed_ms:.2f} ms")
        except Exception as e:
            print(f"  ✗ Skipped {label}: {e}")

    # 2. Print final ranked leaderboard in terminal immediately
    ranked = sorted(solver_runs, key=lambda r: (r["steps"], r["operations"]))
    print("\n" + "=" * 78)
    print(f"FINAL RANKED LEADERBOARD ({len(maze[0])}x{len(maze)} Maze)")
    print("=" * 78)
    header = f"{'Rank':<6} {'Algorithm':<32} {'Steps':<12} {'Operations':<15} {'Time (ms)':<10}"
    print(header)
    print("-" * len(header))

    for rank, r in enumerate(ranked, start=1):
        print(
            f"#{rank:<5} {r['name']:<32} {r['steps']:<12,} "
            f"{r['operations']:<15,} {r['time_ms']:.3f}"
        )

    # 3. Launch the tkinter visualizer AFTER all algorithms have finished
    print("\nLaunching animated visualizer window...")
    PostBenchmarkAnimator(maze, solver_runs).run()
