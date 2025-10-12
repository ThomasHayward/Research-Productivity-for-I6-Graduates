import numpy as np
import statsmodels.api as sm
from statsmodels.discrete.count_model import (ZeroInflatedNegativeBinomialP,
                                              ZeroInflatedPoisson)


def fit_zero_inflated_poisson(y, X):
    """Fit a zero-inflated Poisson regression model."""
    model = ZeroInflatedPoisson(y, X)
    result = model.fit(disp=0)
    return result

def fit_zero_inflated_negbin(y, X):
    """Fit a zero-inflated Negative Binomial regression model."""
    model = ZeroInflatedNegativeBinomialP(y, X)
    result = model.fit(disp=0)
    return result

def print_zip_summary(result):
    return result.summary().as_text()
def print_zip_summary(result):
    return result.summary().as_text()
