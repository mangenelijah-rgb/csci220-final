import json
import math
import random
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MAZE_FILE = PROJECT_ROOT / "maze.json"

# Directions ordered clockwise: 0=North, 1=East, 2=South, 3=West
DIRS = [(0, -1), (1, 0), (0, 1), (-1, 0)]

def find_start_and_end(maze: list[list[int]]):
    start = None
    end = None
    for y, row in enumerate(maze):
        for x, cell in enumerate(row):
            if cell == 2:
                start = (x, y)
            elif cell == 3:
                end = (x, y)
    return start, end

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
        # Connectome-inspired synaptic weights (excitatory > 0, inhibitory < 0)
        self.w_sensor_to_epg = 1.35    # Open corridor excites corresponding compass sector
        self.w_goal_to_epg = 0.85      # Chemosensory food-odor gradient bias
        self.w_epg_to_pfl3 = 1.20      # Compass drives steering layer
        self.w_lateral_inhib = -0.65   # GABAergic ring inhibition (winner-take-all)
        self.w_pfl3_to_dn = 1.40       # Steering neurons excite descending motor neurons
        self.w_memory_inhib = -0.95    # Short-term habituation (avoids repeating dead ends)

        # LIF membrane parameters
        self.tau = 0.82                # Membrane leak factor
        self.v_thresh = 1.0            # Action potential firing threshold

    def decide_turn(self, open_dirs: list[bool], goal_scores: list[float], visit_penalties: list[float]):
        """
        Simulates 25ms (25 time-steps) of spiking neural activity across the fly circuit.
        Returns chosen relative turn (-1=Left, 0=Straight, 1=Right) and total synaptic ops.
        """
        v_epg = [0.0, 0.0, 0.0]
        v_pfl3 = [0.0, 0.0, 0.0]
        v_dn = [0.0, 0.0, 0.0]
        dn_spikes = [0, 0, 0]
        ops = 0

        for _ in range(25):
            epg_spikes = [0, 0, 0]
            pfl3_spikes = [0, 0, 0]

            # 1. Sensory + Food Odor -> EPG Compass Layer
            for i in range(3):
                ops += 1
                if not open_dirs[i]:
                    v_epg[i] = 0.0
                    continue

                sensory_in = self.w_sensor_to_epg
                goal_in = self.w_goal_to_epg * goal_scores[i]
                habituation = self.w_memory_inhib * visit_penalties[i]
                noise = self.rng.uniform(-0.08, 0.08)

                v_epg[i] = self.tau * v_epg[i] + sensory_in + goal_in + habituation + noise
                if v_epg[i] >= self.v_thresh:
                    epg_spikes[i] = 1
                    v_epg[i] = 0.0

            # 2. EPG + GABAergic Lateral Inhibition -> PFL3 Steering Layer
            for i in range(3):
                ops += 1
                other_spikes = sum(epg_spikes) - epg_spikes[i]
                syn_input = (self.w_epg_to_pfl3 * epg_spikes[i]) + (self.w_lateral_inhib * other_spikes)
                v_pfl3[i] = self.tau * v_pfl3[i] + syn_input
                if v_pfl3[i] >= self.v_thresh:
                    pfl3_spikes[i] = 1
                    v_pfl3[i] = 0.0

            # 3. PFL3 -> DNa01/DNa02 Descending Motor Neurons
            for i in range(3):
                ops += 1
                v_dn[i] = self.tau * v_dn[i] + (self.w_pfl3_to_dn * pfl3_spikes[i])
                if v_dn[i] >= self.v_thresh:
                    dn_spikes[i] += 1
                    v_dn[i] = 0.0

        # Pick the valid open direction whose descending motor neuron fired most
        turns = [-1, 0, 1]
        best_turn = None
        best_score = -1e9
        for i, turn in enumerate(turns):
            if open_dirs[i]:
                score = dn_spikes[i] + v_dn[i] + self.rng.uniform(0, 0.05)
                if score > best_score:
                    best_score = score
                    best_turn = turn

        # If all 3 front/side directions are walls (dead end), turn 180 degrees (+2)
        if best_turn is None:
            return 2, ops
        return best_turn, ops

def solve_fruitfly(maze: list[list[int]]):
    start, end = find_start_and_end(maze)
    height = len(maze)
    width = len(maze[0])

    fly_brain = DrosophilaSteeringCircuit()
    x, y = start
    facing = 1  # Start facing East
    path = [(x, y)]
    visit_counts = {(x, y): 1}
    total_operations = 0

    while (x, y) != end:
        total_operations += 1

        open_dirs = []
        goal_scores = []
        visit_penalties = []

        curr_dist = math.hypot(end[0] - x, end[1] - y)

        for turn in (-1, 0, 1):
            total_operations += 1
            cand_dir = (facing + turn) % 4
            dx, dy = DIRS[cand_dir]
            nx, ny = x + dx, y + dy

            if 0 <= nx < width and 0 <= ny < height and maze[ny][nx] != 1:
                open_dirs.append(True)
                next_dist = math.hypot(end[0] - nx, end[1] - ny)
                goal_scores.append(max(-1.0, min(1.0, curr_dist - next_dist)))
                visit_penalties.append(min(3.0, float(visit_counts.get((nx, ny), 0))))
            else:
                open_dirs.append(False)
                goal_scores.append(0.0)
                visit_penalties.append(0.0)

        chosen_turn, neural_ops = fly_brain.decide_turn(open_dirs, goal_scores, visit_penalties)
        total_operations += neural_ops

        facing = (facing + chosen_turn) % 4
        dx, dy = DIRS[facing]
        x, y = x + dx, y + dy

        path.append((x, y))
        visit_counts[(x, y)] = visit_counts.get((x, y), 0) + 1

    return path, total_operations

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

    path, operations = solve_fruitfly(maze)

    print("Labotimized fruitfly: aka my online friend Shapeless Shadow.\n")
    print_solved_maze(maze, path)

    print(f"\nSteps taken: {len(path) - 1}")
    print(f"Total operations: {operations}")
