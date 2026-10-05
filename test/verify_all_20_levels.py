import os
import re
import sys
from collections import deque

DIRS = [(-1, 0), (1, 0), (0, -1), (0, 1)]

def solve_grid(grid, max_states=1000000):
    R, C = len(grid), len(grid[0])
    walls, targets, boxes = set(), set(), set()
    player = None

    for r in range(R):
        for c in range(C):
            v = grid[r][c]
            if v == 1: walls.add((r, c))
            elif v == 2: targets.add((r, c))
            elif v == 3: boxes.add((r, c))
            elif v == 4: boxes.add((r, c)); targets.add((r, c))
            elif v == 5: player = (r, c)
            elif v == 6: player = (r, c); targets.add((r, c))

    if len(targets) != len(boxes) or not player:
        return False, 0, 0, 0

    targets = frozenset(targets)
    init_state = (player, tuple(sorted(boxes)))
    queue = deque([(init_state, 0, 0)])
    visited = {init_state}

    states = 0
    while queue:
        (p_pos, b_tuple), moves, pushes = queue.popleft()
        states += 1
        if states > max_states:
            break

        b_set = set(b_tuple)
        if b_set == targets:
            return True, moves, pushes, states

        pr, pc = p_pos
        for dr, dc in DIRS:
            nr, nc = pr + dr, pc + dc
            if (nr, nc) in walls: continue

            if (nr, nc) in b_set:
                nnr, nnc = nr + dr, nc + dc
                if (nnr, nnc) in walls or (nnr, nnc) in b_set: continue
                # Deadlock detection: non-target corner
                if (nnr, nnc) not in targets:
                    up = (nnr - 1, nnc) in walls
                    down = (nnr + 1, nnc) in walls
                    left = (nnr, nnc - 1) in walls
                    right = (nnr, nnc + 1) in walls
                    if (up or down) and (left or right):
                        continue

                new_b = tuple(sorted((b_set - {(nr, nc)}) | {(nnr, nnc)}))
                nst = ((nr, nc), new_b)
                if nst not in visited:
                    visited.add(nst)
                    queue.append((nst, moves + 1, pushes + 1))
            else:
                nst = ((nr, nc), b_tuple)
                if nst not in visited:
                    visited.add(nst)
                    queue.append((nst, moves + 1, pushes))

    return False, 0, 0, states

def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    c_path = os.path.join(root, "examples", "sokoban", "main.c")
    with open(c_path) as f:
        text = f.read()

    def get_array(name):
        m = re.search(r"static const uint8_t " + name + r"\[\d+\] = \{([^}]+)\};", text)
        raw = m.group(1)
        clean = re.sub(r"/\*.*?\*/", "", raw, flags=re.DOTALL)
        return [int(x.strip(), 16) for x in clean.split(",") if x.strip()]

    la = get_array("levels_a")
    lb = get_array("levels_b")
    lc = get_array("levels_c")
    ld = get_array("levels_d")

    all_bytes = la + lb + lc + ld
    assert len(all_bytes) == 720, f"Expected 720 bytes, got {len(all_bytes)}"

    level_names = [
        "First Push", "The Detour", "Twin Goals", "Pillar Pass", "Split Path",
        "The Chamber", "The Alcove", "The Corridor", "The Lock", "Grandmaster",
        "The Wide Gate", "Twin Courtyards", "The Serpentine", "Central Redoubt", "Split Wing",
        "Fortress 9", "The Dual Pass", "The Warehouse Citadel", "The Great Divide", "Grandmaster 9"
    ]

    print(f"{'Lvl':<4} | {'Name':<24} | {'Moves':<6} | {'Pushes':<7} | {'States':<8} | {'Span (cols)':<12} | {'Status'}")
    print("-" * 75)

    all_solved = True
    prev_moves = 0
    for lvl in range(20):
        chunk = all_bytes[lvl*36:(lvl+1)*36]
        flat = []
        for b in chunk:
            flat.append((b >> 4) & 15)
            flat.append(b & 15)
        g = [flat[r*9:(r+1)*9] for r in range(8)]

        # compute column span of active elements
        active_cols = []
        for r in range(8):
            for c in range(9):
                if g[r][c] in [0, 2, 3, 4, 5, 6]:
                    active_cols.append(c)
        span_str = f"[{min(active_cols)}..{max(active_cols)}]"

        solved, m, p, s = solve_grid(g, max_states=1000000)
        status = "SOLVED" if solved else "FAILED"
        if not solved:
            all_solved = False

        print(f"{lvl+1:<4} | {level_names[lvl]:<24} | {m:<6} | {p:<7} | {s:<8} | {span_str:<12} | {status}")
        prev_moves = m

    print("-" * 75)
    if all_solved:
        print("ALL 20 LEVELS VERIFIED 100% SOLVABLE!")
    else:
        print("ERROR: One or more levels failed to solve!")
        sys.exit(1)

if __name__ == "__main__":
    main()
