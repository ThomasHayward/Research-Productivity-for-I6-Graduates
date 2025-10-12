import numpy as np


def cohens_d(group1, group2):
    """Calculate Cohen's d effect size between two groups."""
    pooled_std = np.sqrt((np.var(group1, ddof=1) + np.var(group2, ddof=1)) / 2)
    return (np.mean(group1) - np.mean(group2)) / pooled_std


def print_cohens_d(group1, group2, label1='Group 1', label2='Group 2'):
    d = cohens_d(group1, group2)
    return (f"Effect Size (Cohen's d) for {label1} vs {label2}: {d:.3f}\n")
