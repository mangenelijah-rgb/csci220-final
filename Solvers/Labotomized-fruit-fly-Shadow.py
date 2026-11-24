import json
import math
import random
import sys
from pathlib import Path
from c_package.c_maze import BitMaze, SolverResult

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAZE_FILE = PROJECT_ROOT / "maze.json"

# Directions ordered clockwise: 0=North, 1=East, 2=South, 3=West
DIRS = ((0, -1), (1, 0), (0, 1), (-1, 0))

class DrosophilaSteeringCircuit:
    """
    Spiking Leaky Integrate-and-Fire (LIF) model based on the Drosophila
    Central Complex (CX) navigation & steering connectome:
      - Sensory Mechanoreceptors (Antennae): detect open corridors
      - EPG (Ellipsoid Body Compass Neurons): encode heading & food-odor gradient
      - PFL3 (Fan-shaped Body Steering Neurons): compare heading vs. goal & open paths
      - DNa01 / DNa02 (Descending Motor Neurons): trigger Left, Straight, or Right turns
    """
    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        self.w_sensor_to_epg = 1.45    # Open corridor excites corresponding compass sector
        self.w_goal_to_epg = 0.45      # Chemosensory food-odor gradient bias
        self.w_epg_to_pfl3 = 1.20      # Compass drives steering layer
        self.w_lateral_inhib = -0.65   # GABAergic ring inhibition (winner-take-all)
        self.w_pfl3_to_dn = 1.40       # Steering neurons excite descending motor neurons
        self.w_memory_inhib = -1.10    # Mushroom Body aversive habituation memory

        # LIF membrane parameters
        self.tau = 0.82                # Membrane leak factor
        self.v_thresh = 1.0            # Action potential firing threshold

    def decide_turn(
        self,
        open_dirs: tuple[bool, bool, bool],
        goal_scores: tuple[float, float, float],
        visit_penalties: tuple[float, float, float],
    ):
        o0, o1, o2 = open_dirs
        open_count = o0 + o1 + o2

        # Dead end or all forward paths sealed: immediate 180-degree U-turn
        if open_count == 0:
            return 2, 75

        # Forced 1-way hallway or bend: only 1 EPG sector receives input
        if open_count == 1:
            if o0:
                return -1, 75
            return (0 if o1 else 1), 75

        # Junction (2 or 3 open paths): run unrolled LIF spiking competition
        tau = self.tau
        v_thresh = self.v_thresh
        w_epg_pfl3 = self.w_epg_to_pfl3
        w_lat = self.w_lateral_inhib
        w_pfl3_dn = self.w_pfl3_to_dn
        rand_uniform = self.rng.uniform

        base0 = (self.w_sensor_to_epg + self.w_goal_to_epg * goal_scores[0] + self.w_memory_inhib * visit_penalties[0]) if o0 else 0.0
        base1 = (self.w_sensor_to_epg + self.w_goal_to_epg * goal_scores[1] + self.w_memory_inhib * visit_penalties[1]) if o1 else 0.0
        base2 = (self.w_sensor_to_epg + self.w_goal_to_epg * goal_scores[2] + self.w_memory_inhib * visit_penalties[2]) if o2 else 0.0

        ve0 = ve1 = ve2 = 0.0
        vp0 = vp1 = vp2 = 0.0
        vd0 = vd1 = vd2 = 0.0
        s0 = s1 = s2 = 0

        ticks = 12
        for _ in range(ticks):
            es0 = es1 = es2 = 0
            if o0:
                ve0 = tau * ve0 + base0 + rand_uniform(-0.08, 0.08)
                if ve0 >= v_thresh:
                    es0 = 1
                    ve0 = 0.0
            if o1:
                ve1 = tau * ve1 + base1 + rand_uniform(-0.08, 0.08)
                if ve1 >= v_thresh:
                    es1 = 1
                    ve1 = 0.0
            if o2:
                ve2 = tau * ve2 + base2 + rand_uniform(-0.08, 0.08)
                if ve2 >= v_thresh:
                    es2 = 1
                    ve2 = 0.0

            ps0 = ps1 = ps2 = 0
            vp0 = tau * vp0 + w_epg_pfl3 * es0 + w_lat * (es1 + es2)
            if vp0 >= v_thresh:
                ps0 = 1
                vp0 = 0.0

            vp1 = tau * vp1 + w_epg_pfl3 * es1 + w_lat * (es0 + es2)
            if vp1 >= v_thresh:
                ps1 = 1
                vp1 = 0.0

            vp2 = tau * vp2 + w_epg_pfl3 * es2 + w_lat * (es0 + es1)
            if vp2 >= v_thresh:
                ps2 = 1
                vp2 = 0.0

            vd0 = tau * vd0 + w_pfl3_dn * ps0
            if vd0 >= v_thresh:
                s0 += 1
                vd0 = 0.0

            vd1 = tau * vd1 + w_pfl3_dn * ps1
            if vd1 >= v_thresh:
                s1 += 1
                vd1 = 0.0

            vd2 = tau * vd2 + w_pfl3_dn * ps2
            if vd2 >= v_thresh:
                s2 += 1
                vd2 = 0.0

        best_turn = 0
        best_score = -1e9
        if o0:
            sc = s0 + vd0 + rand_uniform(0.0, 0.05)
            if sc > best_score:
                best_score = sc
                best_turn = -1
        if o1:
            sc = s1 + vd1 + rand_uniform(0.0, 0.05)
            if sc > best_score:
                best_score = sc
                best_turn = 0
        if o2:
            sc = s2 + vd2 + rand_uniform(0.0, 0.05)
            if sc > best_score:
                best_score = sc
                best_turn = 1

        return best_turn, ticks * 9


def solve_fruitfly(
    maze: BitMaze,
    output_dir: str | Path = PROJECT_ROOT / "results",
    chunk_size: int = 50_000,
) -> SolverResult:
    start = (0, 1)
    height = len(maze)
    width = len(maze[0])
    end = (width - 1, height - 2)
    ex, ey = end
    sx, sy = start

    with SolverResult(
        algorithm="Lobotomized Fruit Fly (Shadow)",
        width=width,
        height=height,
        output_dir=output_dir,
        prefix="fruitfly",
        chunk_size=chunk_size,
    ) as result:
        fly_brain = DrosophilaSteeringCircuit()
        x, y = start
        facing = 1  # Start facing East
        path = [(x, y)]
        result.record_search(x, y)

        visit_counts = {(x, y): 1}
        dead_ends = set()
        hypot = math.hypot

        while (x, y) != end:
            result.operations += 1

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

            chosen_turn, neural_ops = fly_brain.decide_turn((o0, o1, o2), (g0, g1, g2), (p0, p1, p2))
            result.operations += neural_ops + 3

            facing = (facing + chosen_turn) & 3
            dx, dy = DIRS[facing]
            x += dx
            y += dy

            pos = (x, y)
            path.append(pos)
            result.record_search(x, y)
            visit_counts[pos] = visit_counts.get(pos, 0) + 1

        result.set_solution_path(path)
        return result


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
    result = solve_fruitfly(maze)

    print("Labotimized fruitfly: aka my online friend Shapeless Shadow.\n")
    print_solved_maze(maze, result)
    print(f"\nSteps taken: {result.steps}")
    print(f"Total operations: {result.operations}")