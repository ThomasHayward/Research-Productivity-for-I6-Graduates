import numpy as np
from scipy.stats import pearsonr


def pearson_correlation(x, y):
    """
    Compute Pearson correlation coefficient and p-value between two arrays.
    Returns (r, p_value)
    """
    return pearsonr(x, y)


def print_pearson_correlation(x, y, labelx='X', labely='Y'):
    r, p = pearson_correlation(x, y)
    return (f"Pearson correlation between {labelx} and {labely}: r = {r:.3f}, p = {p:.4g}\n")
