import importlib.util
import json
import math
import sys
import tkinter as tk
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SOLVERS_DIR = PROJECT_ROOT / "Solvers"
MAZE_FILE = PROJECT_ROOT / "maze.json"

MAX_WINDOW_PX = 850
STEPS_PER_FRAME = 2500   # Increase to 10000+ to fast-forward on 3501x3501 mazes

# Import DrosophilaSteeringCircuit & DIRS directly from your solver file
spec = importlib.util.spec_from_file_location("fly_mod", SOLVERS_DIR / "Labotomized-fruit-fly-(Shadow).py")
fly_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fly_mod)

DIRS = fly_mod.DIRS
find_start_and_end = fly_mod.find_start_and_end
DrosophilaSteeringCircuit = fly_mod.DrosophilaSteeringCircuit


def solve_fruitfly(maze: list[list[int]]):
    """Generator that runs the Drosophila connectome solver and yields live progress."""
    start, end = find_start_and_end(maze)
    height = len(maze)
    width = len(maze[0])
    ex, ey = end
    sx, sy = start

    fly_brain = DrosophilaSteeringCircuit()
    x, y = start
    facing = 1
    visit_counts = {(x, y): 1}
    dead_ends = set()
    steps = 0
    hypot = math.hypot

    while (x, y) != end:
        # Count open non-dead-end neighbors
        active_exits = 0
        if y > 0 and maze[y - 1][x] != 1 and (x, y - 1) not in dead_ends:
            active_exits += 1
        if x + 1 < width and maze[y][x + 1] != 1 and (x + 1, y) not in dead_ends:
            active_exits += 1
        if y + 1 < height and maze[y + 1][x] != 1 and (x, y + 1) not in dead_ends:
            active_exits += 1
        if x > 0 and maze[y][x - 1] != 1 and (x - 1, y) not in dead_ends:
            active_exits += 1

        if active_exits <= 1 and (x, y) != (sx, sy):
            dead_ends.add((x, y))

        curr_dist = hypot(ex - x, ey - y)
        d_left = (facing - 1) & 3
        d_right = (facing + 1) & 3

        lx, ly = x + DIRS[d_left][0], y + DIRS[d_left][1]
        fx, fy = x + DIRS[facing][0], y + DIRS[facing][1]
        rx, ry = x + DIRS[d_right][0], y + DIRS[d_right][1]

        # Treat sealed dead ends as closed walls unless ALL directions are sealed
        raw_o0 = 0 <= lx < width and 0 <= ly < height and maze[ly][lx] != 1
        raw_o1 = 0 <= fx < width and 0 <= fy < height and maze[fy][fx] != 1
        raw_o2 = 0 <= rx < width and 0 <= ry < height and maze[ry][rx] != 1

        o0 = raw_o0 and (lx, ly) not in dead_ends
        o1 = raw_o1 and (fx, fy) not in dead_ends
        o2 = raw_o2 and (rx, ry) not in dead_ends

        if not (o0 or o1 or o2):
            o0, o1, o2 = raw_o0, raw_o1, raw_o2

        if o0:
            g0 = max(-1.0, min(1.0, curr_dist - hypot(ex - lx, ey - ly)))
            p0 = float(visit_counts.get((lx, ly), 0)) * 2.5
        else:
            g0 = p0 = 0.0

        if o1:
            g1 = max(-1.0, min(1.0, curr_dist - hypot(ex - fx, ey - fy)))
            p1 = float(visit_counts.get((fx, fy), 0)) * 2.5
        else:
            g1 = p1 = 0.0

        if o2:
            g2 = max(-1.0, min(1.0, curr_dist - hypot(ex - rx, ey - ry)))
            p2 = float(visit_counts.get((rx, ry), 0)) * 2.5
        else:
            g2 = p2 = 0.0

        chosen_turn, _ = fly_brain.decide_turn((o0, o1, o2), (g0, g1, g2), (p0, p1, p2))

        facing = (facing + chosen_turn) & 3
        dx, dy = DIRS[facing]
        x += dx
        y += dy

        pos = (x, y)
        steps += 1
        visit_counts[pos] = visit_counts.get(pos, 0) + 1
        yield pos, steps, len(dead_ends), pos in dead_ends


class LiveFlyDebugger:
    def __init__(self, maze: list[list[int]]):
        self.maze = maze
        self.rows = len(maze)
        self.cols = len(maze[0])

        self.step = max(1, math.ceil(max(self.cols, self.rows) / MAX_WINDOW_PX))
        self.img_w = math.ceil(self.cols / self.step)
        self.img_h = math.ceil(self.rows / self.step)
        self.zoom_factor = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.paused = False
        self.history = []
        self.total_steps = 0
        self.sealed_count = 0

        self.root = tk.Tk()
        self.root.title(f"LIVE Fruit Fly Debugger ({self.cols}x{self.rows})")
        self.root.configure(bg="#1e1e1e")

        top_frame = tk.Frame(self.root, bg="#1e1e1e")
        top_frame.pack(fill=tk.X, padx=12, pady=6)

        self.status_var = tk.StringVar(value="Starting live fly...")
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
        self.pause_btn = tk.Button(top_frame, text="Pause (Space)", command=self.toggle_pause, **btn_style)
        self.pause_btn.pack(side=tk.RIGHT, padx=4)

        self.canvas = tk.Canvas(self.root, width=self.img_w, height=self.img_h, bg="#111111", highlightthickness=0)
        self.canvas.pack(padx=12, pady=(0, 12))

        # Controls
        self.root.bind("<space>", lambda e: self.toggle_pause())
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
        self.fly_gen = solve_fruitfly(self.maze)
        self.root.after(50, self.tick)

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
        """Re-projects stored grid coordinates into the current zoom/pan viewport."""
        self.canvas.delete("trail", "head")
        if len(self.history) >= 2:
            step = max(1, len(self.history) // 4000)
            pts = []
            for gx, gy in self.history[::step]:
                pts.extend(self.grid_to_screen(gx, gy))
            if len(pts) >= 4:
                self.canvas.create_line(*pts, fill="#00b0ff", width=max(1, int(self.zoom_factor // 2)), tags="trail")

        if self.history:
            hx, hy = self.grid_to_screen(*self.history[-1])
            r = max(4, int(2 * self.zoom_factor))
            self.canvas.create_oval(hx - r, hy - r, hx + r, hy + r, fill="#ffd600", outline="", tags="head")

    def tick(self):
        if not self.paused:
            batch_pts = []
            last_pos = None
            finished = False

            for _ in range(STEPS_PER_FRAME):
                try:
                    pos, self.total_steps, self.sealed_count, _ = next(self.fly_gen)
                    last_pos = pos
                    self.history.append(pos)
                    batch_pts.extend(self.grid_to_screen(*pos))
                except StopIteration:
                    finished = True
                    break

            if len(batch_pts) >= 4:
                sampled = batch_pts[::max(2, (len(batch_pts) // 200) * 2)]
                if len(sampled) % 2 == 1:
                    sampled = sampled[:-1]
                if len(sampled) >= 4:
                    self.canvas.create_line(*sampled, fill="#00b0ff", width=max(1, int(self.zoom_factor // 2)), tags="trail")

            if last_pos:
                hx, hy = self.grid_to_screen(*last_pos)
                r = max(4, int(2 * self.zoom_factor))
                self.canvas.delete("head")
                self.canvas.create_oval(hx - r, hy - r, hx + r, hy + r, fill="#ffd600", outline="", tags="head")
                self.status_var.set(
                    f"LIVE | Steps: {self.total_steps:,} | Pos: {last_pos} | "
                    f"Dead-ends sealed: {self.sealed_count:,} | Zoom: {self.zoom_factor:.0f}x"
                )

            if finished:
                self.redraw_trail()
                self.status_var.set(
                    f"SOLVED! Total Steps: {self.total_steps:,} | Dead-ends sealed: {self.sealed_count:,}"
                )
                return

        self.root.after(16, self.tick)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    if not MAZE_FILE.exists():
        print("Error: maze.json not found. Run 'python3 main.py' first.")
        sys.exit(1)

    with open(MAZE_FILE, "r") as f:
        maze = json.load(f)

    LiveFlyDebugger(maze).run()
