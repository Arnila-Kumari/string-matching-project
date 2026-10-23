"""
run_all.py - CS570 Final Project Data Collector & Plotter
Runs basic.py and efficient.py on all Datapoints/in*.txt files,
parses time/memory from output, prints a formatted table, saves CSV,
and produces the two Part II.D line plots (CPU time vs M+N, Memory vs M+N).

Usage:
    python3 run_all.py                       # default threshold (10)
    python3 run_all.py --threshold 1000      # tune trivial size threshold
    python3 run_all.py -t 500

Output:
    Creates Results-MM-DD-HH-MM-SS/ containing:
      - results.csv
      - time_vs_size.png
      - memory_vs_size.png
"""

import subprocess
import os
import sys
import csv
import argparse
from datetime import datetime

import matplotlib.pyplot as plt

# CONFIG
DATAPOINTS_DIR = "CSCI570_Project_Minimum_Jul_14/Datapoints"
BASIC_SCRIPT   = "basic.py"
EFFICIENT_SCRIPT = "efficient.py"
PYTHON         = sys.executable          # uses whatever python3 is active
TEMP_OUT_BASIC = "_tmp_basic_out.txt"
TEMP_OUT_EFF   = "_tmp_eff_out.txt"
CSV_NAME       = "results.csv"
TIME_PLOT_NAME = "time_vs_size.png"
MEM_PLOT_NAME  = "memory_vs_size.png"
DEFAULT_THRESHOLD = 10


def parse_output(filepath):
    """Read the 5-line output file and return (time_ms, memory_kb)."""
    with open(filepath) as f:
        lines = [l.strip() for l in f if l.strip()]
    if len(lines) < 5:
        raise ValueError(f"Output file {filepath} has fewer than 5 lines: {lines}")
    time_ms   = float(lines[3])
    memory_kb = float(lines[4])
    return time_ms, memory_kb


def get_string_sizes(input_path):
    """
    Parse the input file and compute len(s1) + len(s2) = M+N.
    Mirrors the generate_string logic in both scripts.
    """
    with open(input_path) as f:
        lines = [l.strip() for l in f if l.strip()]

    base1 = lines[0]
    idx = 1
    indices1 = []
    while idx < len(lines):
        try:
            indices1.append(int(lines[idx]))
            idx += 1
        except ValueError:
            break

    base2 = lines[idx]
    indices2 = [int(lines[i]) for i in range(idx + 1, len(lines))]

    def gen(base, indices):
        t = base
        for j in indices:
            t = t[:j+1] + t + t[j+1:]
        return t

    s1 = gen(base1, indices1)
    s2 = gen(base2, indices2)
    return len(s1) + len(s2)


def run(script, input_file, output_file, extra_args=None):
    """Run `python3 <script> <input> <output> [extra_args...]` and return (time_ms, memory_kb)."""
    cmd = [PYTHON, script, input_file, output_file]
    if extra_args:
        cmd.extend(str(a) for a in extra_args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  !! ERROR running {script} on {input_file}")
        print(f"     stderr: {result.stderr.strip()}")
        return None, None
    return parse_output(output_file)


def make_results_dir():
    """Create a timestamped Results-MM-DD-HH-MM-SS/ folder and return its path."""
    stamp = datetime.now().strftime("%m-%d-%H-%M-%S")
    path = f"Results-{stamp}"
    os.makedirs(path, exist_ok=False)
    return path


def plot_results(rows, threshold, out_dir):
    """Render the two required line plots into out_dir."""
    rows_sorted = sorted(rows, key=lambda r: r[0])
    sizes   = [r[0] for r in rows_sorted]
    t_basic = [r[1] for r in rows_sorted]
    t_eff   = [r[2] for r in rows_sorted]
    m_basic = [r[3] for r in rows_sorted]
    m_eff   = [r[4] for r in rows_sorted]

    eff_label = f"Efficient (trivial threshold = {threshold})"

    # CPU time vs problem size
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(sizes, t_basic, marker="o", label="Basic")
    ax.plot(sizes, t_eff,   marker="s", label=eff_label)
    ax.set_xlabel("Problem size (M + N)")
    ax.set_ylabel("CPU time (ms)")
    ax.set_title("CPU time vs problem size")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, TIME_PLOT_NAME), dpi=150)
    plt.close(fig)

    # Memory vs problem size
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(sizes, m_basic, marker="o", label="Basic")
    ax.plot(sizes, m_eff,   marker="s", label=eff_label)
    ax.set_xlabel("Problem size (M + N)")
    ax.set_ylabel("Memory usage (KB)")
    ax.set_title("Memory usage vs problem size")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, MEM_PLOT_NAME), dpi=150)
    plt.close(fig)


def parse_args():
    p = argparse.ArgumentParser(description="Run basic.py and efficient.py on all datapoints and plot results.")
    p.add_argument("-t", "--threshold", type=int, default=DEFAULT_THRESHOLD,
                   help=f"Trivial problem size threshold for efficient.py (default: {DEFAULT_THRESHOLD})")
    p.add_argument("--datapoints-dir", default=DATAPOINTS_DIR,
                   help=f"Directory containing in*.txt input files (default: {DATAPOINTS_DIR})")
    return p.parse_args()


def main():
    args = parse_args()
    threshold = args.threshold
    datapoints_dir = args.datapoints_dir

    # Collect all input files, sorted numerically (in1, in2, ..., in15)
    files = sorted(
        [f for f in os.listdir(datapoints_dir) if f.startswith("in") and f.endswith(".txt")],
        key=lambda x: int(x.replace("in", "").replace(".txt", ""))
    )

    if not files:
        print(f"No input files found in {datapoints_dir}/")
        sys.exit(1)

    out_dir = make_results_dir()
    print(f"\nResults folder: {out_dir}")
    print(f"Efficient trivial-size threshold: {threshold}")

    rows = []

    print(f"\n{'M+N':>6}  {'Time Basic(ms)':>16}  {'Time Eff(ms)':>14}  {'Mem Basic(KB)':>14}  {'Mem Eff(KB)':>12}")
    print("-" * 72)

    for fname in files:
        input_path = os.path.join(datapoints_dir, fname)
        mn = get_string_sizes(input_path)

        print(f"  Running {fname} (M+N={mn})...", end=" ", flush=True)

        t_basic,  m_basic  = run(BASIC_SCRIPT,     input_path, TEMP_OUT_BASIC)
        t_eff,    m_eff    = run(EFFICIENT_SCRIPT, input_path, TEMP_OUT_EFF, extra_args=[threshold])

        if None in (t_basic, m_basic, t_eff, m_eff):
            print("SKIPPED (error above)")
            continue

        print("done")
        rows.append((mn, t_basic, t_eff, m_basic, m_eff))

    # Clean up temp files
    for f in (TEMP_OUT_BASIC, TEMP_OUT_EFF):
        if os.path.exists(f):
            os.remove(f)

    if not rows:
        print("\nNo successful runs - skipping CSV/plot output.")
        sys.exit(1)

    # PRINT FINAL TABLE
    print(f"\n{'-'*72}")
    print(f"{'M+N':>6}  {'Time Basic(ms)':>16}  {'Time Eff(ms)':>14}  {'Mem Basic(KB)':>14}  {'Mem Eff(KB)':>12}")
    print(f"{'-'*72}")
    for mn, tb, te, mb, me in rows:
        print(f"{mn:>6}  {tb:>16.2f}  {te:>14.2f}  {mb:>14.2f}  {me:>12.2f}")
    print(f"{'-'*72}")

    # SAVE CSV
    csv_path = os.path.join(out_dir, CSV_NAME)
    with open(csv_path, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([f"# trivial_threshold={threshold}"])
        writer.writerow(["M+N", "Time Basic (ms)", "Time Efficient (ms)",
                         "Memory Basic (KB)", "Memory Efficient (KB)"])
        writer.writerows(rows)
    print(f"\nSaved CSV  -> {csv_path}")

    # SAVE PLOTS
    plot_results(rows, threshold, out_dir)
    print(f"Saved plot -> {os.path.join(out_dir, TIME_PLOT_NAME)}")
    print(f"Saved plot -> {os.path.join(out_dir, MEM_PLOT_NAME)}")


if __name__ == "__main__":
    main()
