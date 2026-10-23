import time
import psutil
import sys

## CONSTANTS

DELTA = 30
ALPHA = {
    'A': {'A': 0,   'C': 110, 'G': 48,  'T': 94},
    'C': {'A': 110, 'C': 0,   'G': 118, 'T': 48},
    'G': {'A': 48,  'C': 118, 'G': 0,   'T': 110},
    'T': {'A': 94,  'C': 48,  'G': 110, 'T': 0}
}

## MEMORY AND TIME FUNCTIONS

def process_memory():
    process = psutil.Process()
    memory_info = process.memory_info()
    return float(memory_info.rss / 1024)  # KB

## STRING GENERATOR

def parse_input(filepath):
    with open(filepath) as f:
        lines = [line.strip() for line in f if line.strip()]

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

    return base1, indices1, base2, indices2

def generate_string(base, indices):
    t = base
    for j in indices:
        t = t[:j+1] + t + t[j+1:]
    return t


## GENERAL COST OF ALIGNMENT FUNCTION
def cost_of_alignment(X, Y):
    """
    Returns m x n DP array of alignment cost between input string X (size m) and Y (size n)
    
    input:
        X (str) - sequence 1
        Y (str) - sequence 2
        
    returns:
        dp (list) - m x n dp array
    """
    
    m, n = len(X), len(Y)

    # INITIALIZE DP TABLE
    # dp = [[0] * (n + 1) for _ in range(m + 1)]
    dp = []
    for i in range(m+1):
        row = []
        for j in range(n+1):
            row.append(0)
        dp.append(row)

    # BASE CASES 
    # All 0-row and 0-col are assigned (delta * index)
    #  which represents the trivial cost of aligning any string X with an empty string Y
    for i in range(m + 1):
        dp[i][0] = i * DELTA
    for j in range(n + 1):
        dp[0][j] = j * DELTA

    # RECURRENCE RELATION
    #
    # OPT(i, j) = min (
    #    OPT(i-1, j-1) + alpha_xi_yi    # x_i and y_i are matched at a cost alpha_xi_yi
    #    OPT(i-1, j) + delta            # x_i is not matched, a gap penalty is used
    #    OPT(i, j-1) + delta            # y_i is not matched, a gap penalty is used
    # )
    # 
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            match = ALPHA[X[i - 1]][Y[j - 1]] + dp[i - 1][j - 1]
            gap_in_y = DELTA + dp[i - 1][j]
            gap_in_x = DELTA + dp[i][j - 1]
            dp[i][j] = min(match, gap_in_x, gap_in_y)
            
    return dp

def efficient_cost_of_alignment(X, Y):
    """
    Computes the cost of alignment in a single 1D column
    """
    m, n = len(X), len(Y)

    # Column 0: cost of aligning X[:0] with Y[:j] for each j (which is j * DELTA)
    prev = [j * DELTA for j in range(n + 1)]

    for i in range(1, m + 1):
        curr = [i * DELTA] + [0] * n
        for j in range(1, n + 1):
            match = ALPHA[X[i - 1]][Y[j - 1]] + prev[j - 1]
            gap_in_y = DELTA + prev[j]
            gap_in_x = DELTA + curr[j - 1]
            curr[j] = min(match, gap_in_x, gap_in_y)
        prev = curr

    return prev


## BASIC SEQUENCE ALIGNMENT (USED FOR BASE CASES)

def sequence_alignment(X, Y):
    """
    Align sequences X and Y with DP. This is the basic, non-memory efficient implementation.
    Version: 05-22-01
    
    Returns:
        cost (int): minimum alignment cost.
        aligned_X (list[str]): X with '_' inserted for gaps.
        aligned_Y (list[str]): Y with '_' inserted for gaps.
    """
    m, n = len(X), len(Y)
    dp = cost_of_alignment(X, Y)

    # TOP-DOWN PASS
    # The alignment is reconstructed from top-right based on the DP array values
    aligned_X, aligned_Y = [], []
    i, j = m, n
    while i > 0 and j > 0: 
        
        # Case 1: x_i-1 and y_j-1 was matched at a cost alpha_(xi-1,yj-1)
        # So we include x_i-1 and y_j-1 in the alignment
        if dp[i][j] == ALPHA[X[i - 1]][Y[j - 1]] + dp[i - 1][j - 1]:
            aligned_X.append(X[i - 1])
            aligned_Y.append(Y[j - 1])
            i -= 1
            j -= 1 
        
        # Case 2: x_i-1 was not matched, 
        # so x_i-1 is 'matched' with a gap __
        elif dp[i][j] == DELTA + dp[i - 1][j]:
            aligned_X.append(X[i - 1])
            aligned_Y.append('_')
            i -= 1
            
        # Case 3: y_j-1 was not matched,
        #  so y_j-1 is matched with a gap __
        else:
            aligned_X.append('_')
            aligned_Y.append(Y[j - 1])
            j -= 1
    
    # If there are still x characters remaining, 
    #  they are matched with a gap
    while i > 0:
        aligned_X.append(X[i - 1])
        aligned_Y.append('_')
        i -= 1

    # If there are still y characters remaining,
    #  they are matched with a gap
    while j > 0:
        aligned_X.append('_')
        aligned_Y.append(Y[j - 1])
        j -= 1
    
    # The overall alignment cost is stored in the top-right corner of the table
    cost = dp[m][n]
    
    # Since we aligned the strings in reverse order, we reverse them again to 
    #  show them in the original sequence order
    aligned_X = aligned_X[::-1]
    aligned_Y = aligned_Y[::-1]
    
    # Finally we join the lists into a single string
    aligned_X = ''.join(aligned_X) 
    aligned_Y = ''.join(aligned_Y)

    return cost, aligned_X, aligned_Y


## MEMORY-EFFICIENT SEQUENCE ALIGNMENT
    
def divide_and_conquer_sequence(X, Y, peak_kb, trivial_size_threshold=100):

    m, n = len(X), len(Y)

    if n * m <= trivial_size_threshold or m<=1:
        return sequence_alignment(X, Y)

    # Split X into X_L and X_R
    X_L = X[:m // 2]
    X_R = X[m // 2:]

    # DP cost of aligning X_L against every prefix Y[:k]
    last_col_1 = efficient_cost_of_alignment(X_L, Y)

    # DP cost of aligning X_R against every prefix/substring Y[:k]
    #  note we reverse X_R and Y so we can use the same reurrence formula
    last_col_2 = efficient_cost_of_alignment(X_R[::-1], Y[::-1])

    # Sample peak memory
    peak_kb[0] = max(peak_kb[0], process_memory())

    # For each split point k in Y (Y_L = Y[:k], Y_R = Y[k:]),
    #  total cost = cost(X_L, Y[:k]) + cost(X_R, Y[k:])
    combined = [last_col_1[k] + last_col_2[n - k] for k in range(n + 1)]

    # The optimal k value is the index of the lowest cost
    k = combined.index(min(combined))

    # Since we found the optimal split, we know Y_L and Y_R:
    Y_L = Y[:k]
    Y_R = Y[k:]

    cost_left, aligned_x_left, aligned_y_left = divide_and_conquer_sequence(X_L, Y_L, peak_kb, trivial_size_threshold)
    cost_right, aligned_x_right, aligned_y_right = divide_and_conquer_sequence(X_R, Y_R, peak_kb, trivial_size_threshold)

    cost_total = cost_left + cost_right
    aligned_x = aligned_x_left + aligned_x_right
    aligned_y = aligned_y_left + aligned_y_right

    return cost_total, aligned_x, aligned_y


def efficient_sequence_alignment(X, Y, trivial_size_threshold=100):
    """
    Align sequences X and Y via divide-and-conquer in O(m+n) space.

    Args:
        X (str): sequence string 1
        Y (str): sequence string 2
        trivial_size_threshold (int): threshold for i*j trivial problem size (base case)

    Returns:
        cost (int): minimum alignment cost.
        memory_used_kb (float): peak resident memory observed during alignment, in KB.
        aligned_X (str): X with '_' inserted for gaps.
        aligned_Y (str): Y with '_' inserted for gaps.
    """

    # Create the memory tracker and initialize with current process memory (for baseline)
    peak_kb = [process_memory()]

    cost_total, aligned_x, aligned_y = divide_and_conquer_sequence(
        X, Y, peak_kb, trivial_size_threshold
    )

    return cost_total, peak_kb[0], aligned_x, aligned_y


def save_results(output_path, cost, aligned_X, aligned_Y, time_taken_ms, memory_used_kb):
    # Write the 5 required lines to output file
    with open(output_path, 'w') as f:
        f.write(f"{cost}\n")              # 1. cost of alignment (int)
        f.write(f"{aligned_X}\n")         # 2. aligned string 1
        f.write(f"{aligned_Y}\n")         # 3. aligned string 2
        f.write(f"{time_taken_ms}\n")     # 4. time in ms
        f.write(f"{memory_used_kb}\n")    # 5. memory in KB


## MAIN

def main(input_path, output_path, trivial_size_threshold=100):
    base1, indices1, base2, indices2 = parse_input(input_path)
    s1 = generate_string(base1, indices1)
    s2 = generate_string(base2, indices2)

    #Mesaure time and memory

    start_time = time.time()
    cost, memory_used_kb, aligned_X, aligned_Y = efficient_sequence_alignment(s1, s2, trivial_size_threshold)
    end_time = time.time()

    time_taken_ms = (end_time - start_time) * 1000

    save_results(output_path, cost, aligned_X, aligned_Y, time_taken_ms, memory_used_kb)


if __name__ == "__main__":
    
    # EXPERIMENT WITH THIS VALUE
    #  This is the m*n size where we use the basic (non-efficient) base case
    default_threshold = 10
    
    threshold = int(sys.argv[3]) if len(sys.argv) > 3 else default_threshold
    main(sys.argv[1], sys.argv[2], threshold)
