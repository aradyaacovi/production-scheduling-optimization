"""Command-line entry point.

    python scheduling_cli.py --input examples/Input_Data_File_1_Example --output result
    python scheduling_cli.py --input examples/Input_Data_File_1_Example --output result --baseline-only

File names are given without the .xlsx extension, as in Run_GA / Run_Solver.
"""

import argparse

from Tapi_Project_GA_Engine import Run_GA
from Tapi_Project_Solver_Engine import Run_Solver


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Single-machine just-in-time scheduling (genetic algorithm + LP)."
    )
    parser.add_argument("--input", required=True, help="input workbook, without .xlsx")
    parser.add_argument("--output", required=True, help="output workbook, without .xlsx")
    parser.add_argument(
        "--baseline-only",
        action="store_true",
        help="solve only the input order with the LP (no genetic algorithm)",
    )
    args = parser.parse_args(argv)

    if args.baseline_only:
        Run_Solver(args.input, args.output)
        print(f"Baseline written to {args.output}.xlsx")
    else:
        sequence, penalty = Run_GA(args.input, args.output)
        print(f"Best penalty {penalty:.1f}; written to {args.output}.xlsx")


if __name__ == "__main__":
    main()
