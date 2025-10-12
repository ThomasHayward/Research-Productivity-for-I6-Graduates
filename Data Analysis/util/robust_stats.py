import numpy as np
from scipy import stats


def median_iqr(group):
    """Return median and IQR (Q1, Q3) for a group."""
    median = np.median(group)
    q1 = np.percentile(group, 25)
    q3 = np.percentile(group, 75)
    return median, q1, q3

def print_median_iqr(group, label='Group'):
    median, q1, q3 = median_iqr(group)
    return f"{label}: median = {median:.2f}, IQR = [{q1:.2f}, {q3:.2f}]\n"

def prop_above_threshold(group, threshold=1):
    """Return proportion and count of group >= threshold."""
    group = np.array(group)
    count = np.sum(group >= threshold)
    total = len(group)
    prop = count / total if total > 0 else np.nan
    return prop, count, total

def print_prop_above_threshold(group, label='Group', threshold=1):
    prop, count, total = prop_above_threshold(group, threshold)
    return f"{label}: {count}/{total} ({prop*100:.1f}%) have >= {threshold} publications\n"
    return f"{label}: {count}/{total} ({prop*100:.1f}%) have >= {threshold} publications\n"
