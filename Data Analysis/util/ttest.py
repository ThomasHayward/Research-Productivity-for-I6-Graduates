import numpy as np
from scipy import stats


def ttest_summary(group1, group2):
    """Standard t-test for difference in means (two-sided, unequal variance)"""
    return stats.ttest_ind(group1, group2, alternative= 'greater',equal_var=False)

def print_ttest_summary(group1, group2, label1='Group 1', label2='Group 2'):
    t_stat, p_val = ttest_summary(group1, group2)
    return (f"T-test for difference in means ({label1} vs {label2}):\n"
            f"t-statistic: {t_stat:.3f}, p-value: {p_val:.4f}\n")

def welchs_ttest(group1, group2):
    """Welch's t-test (one-sided, greater)"""
    return stats.ttest_ind(group1, group2, alternative='greater', equal_var=False)

def print_welchs_ttest(group1, group2, label1='Group 1', label2='Group 2'):
    t_stat, p_val = welchs_ttest(group1, group2)
    return (f"Welch's t-test ({label1} > {label2}):\n"
            f"t-statistic: {t_stat:.3f}, p-value: {p_val:.4f}\n")
