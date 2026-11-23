"""Baseline vs genetic algorithm on seeded random instances.

    python benchmarks/benchmark.py            # sizes 10, 15, 20; 10 s per GA run

Instances are generated here (seeded), written in the input-file layout, and
solved with the same Run_Solver / Run_GA as the real program.
"""

import os
import random
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openpyxl import Workbook, load_workbook  # noqa: E402

from Tapi_Project_GA_Engine import Run_GA  # noqa: E402
from Tapi_Project_Solver_Engine import Run_Solver  # noqa: E402

SIZES = (10, 15, 20)
SEEDS = (1, 2, 3)
TIME_LIMIT = 10


def make_instance(path, n, seed):
    rnd = random.Random(seed)
    t = [rnd.randint(2, 20) for _ in range(n)]
    horizon = sum(t)
    d = [rnd.randint(t[j], horizon) for j in range(n)]
    v = [rnd.randint(1, 10) for _ in range(n)]
    w = [rnd.randint(1, 10) for _ in range(n)]
    ws_book = Workbook()
    ws = ws_book.active
    for row, values in enumerate(((range(1, n + 1)), t, d, v, w), start=1):
        for col, value in enumerate(values, start=2):
            ws.cell(row=row, column=col, value=value)
    ws["A7"], ws["A9"], ws["A11"], ws["A13"] = 20, 2, 0.2, TIME_LIMIT
    ws_book.save(path + ".xlsx")


def penalty_of(path):
    return load_workbook(path + ".xlsx", data_only=True).active["B12"].value


def main():
    work = tempfile.mkdtemp(prefix="bench-")
    print("| Jobs | Seed | Baseline | GA | Change |")
    print("|---|---|---|---|---|")
    try:
        for n in SIZES:
            for seed in SEEDS:
                base = os.path.join(work, f"inst_{n}_{seed}")
                make_instance(base, n, seed)
                Run_Solver(base, base + "_base")
                Run_GA(base, base + "_ga")
                b, g = penalty_of(base + "_base"), penalty_of(base + "_ga")
                change = f"{(g - b) / b:+.0%}" if b else "-"
                print(f"| {n} | {seed} | {b:.0f} | {g:.0f} | {change} |", flush=True)
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
