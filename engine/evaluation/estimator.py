import math

def pass_at_k(n: int, c: int, k: int) -> float:
    """Calculate the pass@k metric.
    
    Using the unbiased estimator from the Codex/HumanEval paper:
      pass@k = 1 - C(n-c, k) / C(n, k)
      
    Where:
      n = total samples (n >= 1)
      c = correct samples (0 <= c <= n)
      k = the k parameter (k >= 1)
      
    If n - c < k, it returns 1.0 because all selections of k samples must include
    at least one correct sample.
    """
    if n <= 0 or k <= 0:
        return 0.0
    if c >= n:
        return 1.0
    if c <= 0:
        return 0.0
    if k > n:
        # If we request more samples than available, if we have at least one success
        # it is technically 1.0, otherwise 0.0.
        return 1.0 if c > 0 else 0.0

    if n - c < k:
        return 1.0

    try:
        num = math.comb(n - c, k)
        den = math.comb(n, k)
        return 1.0 - (num / den)
    except Exception:
        return 0.0
