import numpy as np


def odds_ratio_from_logit(model, param_name='total_publications'):
    """
    Calculate odds ratio and 95% CI from a fitted statsmodels Logit model.
    Returns (odds_ratio, lower_CI, upper_CI)
    """
    odds_ratio = np.exp(model.params[param_name])
    conf_ints = np.exp(model.conf_int().loc[param_name])
    return odds_ratio, conf_ints[0], conf_ints[1]

def print_odds_ratio(model, param_name='total_publications'):
    odds_ratio, lower, upper = odds_ratio_from_logit(model, param_name)
    percent = (odds_ratio - 1) * 100
    return (f"Odds Ratio: {odds_ratio:.3f}\n"
            f"95% CI: ({lower:.3f}, {upper:.3f})\n"
            f"Interpretation: For each additional {param_name.replace('_', ' ')}, the odds increase by {percent:.1f}%\n")