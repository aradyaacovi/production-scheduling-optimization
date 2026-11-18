"""Smoke tests for the GA + LP scheduling project.

Checks that the modules import, that the LP reproduces the known penalty of the
bundled example input, that the GA operators keep permutations valid, and that a
short end-to-end GA run writes a readable results workbook.

No test framework needed. Run it with:

    python tests/test_smoke.py

Exits with status 0 if every check passes, 1 otherwise.
"""

import os
import shutil
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLE_BASE = os.path.join(REPO_ROOT, "examples", "Input_Data_File_1_Example")

# The project modules sit at the repository root and import each other by plain
# module name, so the root has to be importable.
sys.path.insert(0, REPO_ROOT)

PASSED = 0
FAILED = []


def check(label, condition, detail=""):
    """Records one assertion and prints its result."""
    global PASSED
    if condition:
        PASSED += 1
        print(f"  ok   {label}")
    else:
        FAILED.append(label)
        print(f"  FAIL {label}" + (f" -> {detail}" if detail else ""))


def section(title):
    print(f"\n{title}")


# ---------------------------------------------------------------------------
# 1. Imports
# ---------------------------------------------------------------------------
section("Imports")

import Tapi_Project_Utils as utils  # noqa: E402
import Tapi_Project_GA_Engine as ga_engine  # noqa: E402
import Tapi_Project_Solver_Engine as solver_engine  # noqa: E402

check("Tapi_Project_Utils imports", utils is not None)
check("Tapi_Project_GA_Engine imports", ga_engine is not None)
check("Tapi_Project_Solver_Engine imports", solver_engine is not None)
check("Run_GA is callable", callable(ga_engine.Run_GA))
check("Run_Solver is callable", callable(solver_engine.Run_Solver))

# ---------------------------------------------------------------------------
# 2. Reading the bundled example input
# ---------------------------------------------------------------------------
section("Reading examples/Input_Data_File_1_Example.xlsx")

t, d, v, w, labels = utils._read_input_from_workbook_pandas(EXAMPLE_BASE + ".xlsx")

check("10 jobs read", len(t) == 10, f"got {len(t)}")
check("t, d, v, w have equal length", len(t) == len(d) == len(v) == len(w))
check("job labels are 1..10", labels == list(range(1, 11)), f"got {labels}")
check("processing times match the file", t == [2, 7, 9, 4, 5, 19, 7, 12, 19, 11], f"got {t}")
check("due dates match the file", d == [3, 9, 5, 20, 22, 31, 39, 63, 93, 100], f"got {d}")

# ---------------------------------------------------------------------------
# 3. The LP sub-problem on the input order (Stage 1)
# ---------------------------------------------------------------------------
section("LP sub-problem, jobs in input order")

n = len(t)
sequence = list(range(n))
obj, completion, earliness, tardiness = utils.solve_lp_subproblem(sequence, t, d, v, w)

check("LP returns a penalty", obj is not None)
check("LP penalty is 250 for the input order", abs(obj - 250) < 1e-6, f"got {obj}")
check("one completion time per job", len(completion) == n)
check(
    "machine order is respected",
    all(
        completion[sequence[i]] - t[sequence[i]] >= completion[sequence[i - 1]] - 1e-6
        for i in range(1, n)
    ),
)
check("no job starts before time 0", all(completion[j] - t[j] >= -1e-6 for j in range(n)))
check(
    "earliness and tardiness are consistent with d - C",
    all(
        abs((earliness[j] - tardiness[j]) - (d[j] - completion[j])) < 1e-6
        for j in range(n)
    ),
)
check(
    "penalty equals the sum of weighted earliness and tardiness",
    abs(obj - sum(v[j] * earliness[j] + w[j] * tardiness[j] for j in range(n))) < 1e-6,
)

# ---------------------------------------------------------------------------
# 4. GA operators keep permutations valid
# ---------------------------------------------------------------------------
section("GA operators")

parent1 = list(range(n))
parent2 = [9, 4, 7, 1, 0, 3, 8, 2, 6, 5]
for trial in range(50):
    child1, child2 = utils.crossover_ox(parent1, parent2)
    if sorted(child1) != list(range(n)) or sorted(child2) != list(range(n)):
        check("OX crossover always returns valid permutations", False, f"trial {trial}")
        break
else:
    check("OX crossover always returns valid permutations (50 trials)", True)

chromosome = list(range(n))
for _ in range(50):
    utils.mutate_swap(chromosome, 1.0)
check("swap mutation keeps a valid permutation", sorted(chromosome) == list(range(n)))

unchanged = list(range(n))
utils.mutate_swap(unchanged, 0.0)
check("mutation probability 0 changes nothing", unchanged == list(range(n)))

evaluated = [([0, 1], 10.0), ([1, 0], 5.0), ([0, 1], 7.0)]
sorted_pop, probabilities = utils.get_ranking_probabilities(evaluated)
check("ranking sorts best (lowest penalty) first", sorted_pop[0][1] == 5.0)
check("ranking probabilities sum to 1", abs(sum(probabilities) - 1.0) < 1e-9)
check("better solutions get a higher weight", probabilities[0] > probabilities[-1])

parents = utils.select_parents(sorted_pop, probabilities, 2)
check("select_parents returns the requested number", len(parents) == 2)
check("select_parents returns sequences, not pairs", all(isinstance(p, list) for p in parents))

# ---------------------------------------------------------------------------
# 5. GA parameter validation
# ---------------------------------------------------------------------------
section("GA parameter validation")

check("valid parameters pass unchanged", utils._validate_ga_parameters(26, 2) == (26, 2))
check("odd population size is rounded up", utils._validate_ga_parameters(25, 2)[0] == 26)

for bad_pop, label in ((19, "below 20"), (201, "above 200")):
    try:
        utils._validate_ga_parameters(bad_pop, 2)
        check(f"population size {label} is rejected", False)
    except ValueError:
        check(f"population size {label} is rejected", True)

try:
    utils._validate_ga_parameters(100, 1)
    check("elite size below 2 is rejected", False)
except ValueError:
    check("elite size below 2 is rejected", True)

try:
    utils._validate_ga_parameters(100, 11)
    check("elite size above 10% of the population is rejected", False)
except ValueError:
    check("elite size above 10% of the population is rejected", True)

try:
    utils._parse_ga_int(None, "pop_size")
    check("a missing integer parameter is rejected", False)
except ValueError:
    check("a missing integer parameter is rejected", True)

try:
    utils._parse_ga_int(2.5, "pop_size")
    check("a non-integer population size is rejected", False)
except ValueError:
    check("a non-integer population size is rejected", True)

check("_parse_ga_float reads a decimal", utils._parse_ga_float(0.2, "mutation_prob") == 0.2)

# ---------------------------------------------------------------------------
# 6. The LP cache
# ---------------------------------------------------------------------------
section("LP result cache")

utils.lp_cache.clear()
first = utils._get_cached_lp_solution(sequence, t, d, v, w)
check("the first solve fills the cache", tuple(sequence) in utils.lp_cache)
second = utils._get_cached_lp_solution(sequence, t, d, v, w)
check("the same sequence returns the cached result", first is second)
utils.lp_cache.clear()

# ---------------------------------------------------------------------------
# 7. End to end: Stage 1 and a short GA run both write a workbook
# ---------------------------------------------------------------------------
section("End-to-end runs")

from openpyxl import Workbook, load_workbook  # noqa: E402

workdir = tempfile.mkdtemp(prefix="scheduling-smoke-")
try:
    stage1_out = os.path.join(workdir, "stage1")
    solver_engine.Run_Solver(EXAMPLE_BASE, stage1_out)
    check("Run_Solver writes a workbook", os.path.exists(stage1_out + ".xlsx"))

    ws = load_workbook(stage1_out + ".xlsx", data_only=True).active
    check("Stage 1 sheet is named Results", ws.title == "Results")
    check("Stage 1 total penalty is 250", ws["B12"].value == 250, f"got {ws['B12'].value}")
    check("Stage 1 reports no generations", ws["B14"].value == "-")
    check("the sheet has a Gantt row", ws["A17"].value == "Gantt:")

    # A copy of the example input with a 3-second limit, so the GA path runs
    # end to end without holding up CI for the example file's 100 seconds.
    src = load_workbook(EXAMPLE_BASE + ".xlsx", data_only=True).active
    quick = Workbook()
    quick_ws = quick.active
    for row in src.iter_rows(min_row=1, max_row=13, max_col=11):
        for cell in row:
            quick_ws.cell(row=cell.row, column=cell.column, value=cell.value)
    quick_ws["A7"] = 20     # population size
    quick_ws["A9"] = 2      # elite solutions
    quick_ws["A11"] = 0.2   # mutation probability
    quick_ws["A13"] = 3     # time limit, seconds
    quick_base = os.path.join(workdir, "quick_input")
    quick.save(quick_base + ".xlsx")

    ga_out = os.path.join(workdir, "ga_result")
    best_sequence, best_penalty = ga_engine.Run_GA(quick_base, ga_out)

    check("Run_GA writes a workbook", os.path.exists(ga_out + ".xlsx"))
    check("the best sequence is a valid permutation", sorted(best_sequence) == list(range(n)))
    check(
        "the GA never reports worse than the input order",
        best_penalty <= 250 + 1e-6,
        f"got {best_penalty}",
    )

    ga_ws = load_workbook(ga_out + ".xlsx", data_only=True).active
    check("the GA sheet records the baseline as 250", ga_ws["B13"].value == 250)
    check(
        "the GA sheet's total penalty matches the returned value",
        abs(ga_ws["B12"].value - best_penalty) < 1e-6,
    )
    check("the GA sheet counts at least one generation", ga_ws["B14"].value >= 1)
finally:
    shutil.rmtree(workdir, ignore_errors=True)

# ---------------------------------------------------------------------------
section("Summary")
print(f"  {PASSED} checks passed, {len(FAILED)} failed")
if FAILED:
    for label in FAILED:
        print(f"  failed: {label}")
    sys.exit(1)
print("  all checks passed")
