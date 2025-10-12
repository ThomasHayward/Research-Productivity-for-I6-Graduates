from scipy import stats


def mannwhitney_test(group1, group2):
    """Mann-Whitney U test (one-sided, greater)"""
    return stats.mannwhitneyu(group1, group2, alternative='greater')


def print_mannwhitney(group1, group2, label1='Group 1', label2='Group 2'):
    stat, p_val = mannwhitney_test(group1, group2)
    return (f"Mann-Whitney U test ({label1} > {label2}):\n"
            f"Statistic: {stat:.3f}, p-value: {p_val:.4f}\n")
