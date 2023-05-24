"""Percentile calculation functions."""

import numpy as np
import pandas as pd
from hyswap.utils import filter_data_by_time
from hyswap.utils import calculate_metadata


def calculate_fixed_percentile_thresholds(
        data,
        percentiles=np.array((0, 5, 10, 25, 75, 90, 95, 100)),
        method='weibull',
        **kwargs):
    """Calculate fixed percentile thresholds using historic data.

    Parameters
    ----------
    data : array_like
        1D array of data from which to calculate percentile thresholds.

    percentiles : array_like, optional
        Percentiles to calculate. Default is (0, 5, 10, 25, 75, 90, 95, 100).

    method : str, optional
        Method to use to calculate percentiles. Default is 'weibull'.

    **kwargs : dict, optional
        Additional keyword arguments to pass to `numpy.percentile`.

    Returns
    -------
    percentiles : array_like
        Percentiles of the data.

    Examples
    --------
    Calculate default percentile thresholds from some synthetic data.

    .. doctest::

        >>> data = np.arange(101)
        >>> results = percentiles.calculate_fixed_percentile_thresholds(
        ...     data, method='linear')
        >>> results
        array([  0.,   5.,  10.,  25.,  75.,  90.,  95., 100.])

    Calculate a different set of thresholds from some synthetic data.

    .. doctest::

        >>> data = np.arange(101)
        >>> results = percentiles.calculate_fixed_percentile_thresholds(
        ...     data, percentiles=np.array((0, 10, 50, 90, 100)))
        >>> results
        array([  0. ,   9.2,  50. ,  90.8, 100. ])
    """
    return np.percentile(data, percentiles, method=method, **kwargs)


def calculate_variable_percentile_thresholds_by_day(
        df,
        data_column_name,
        percentiles=np.array((0, 5, 10, 25, 75, 90, 95, 100)),
        method='weibull',
        date_column_name=None,
        min_years=10,
        **kwargs):
    """Calculate variable percentile thresholds of data by day of year.

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame containing data to calculate daily percentile thresholds for.

    data_column_name : str
        Name of column containing data to analyze.

    percentiles : array_like, optional
        Percentile thresholds to calculate, default is
        (0, 5, 10, 25, 75, 90, 95, 100).

    method : str, optional
        Method to use to calculate percentiles. Default is 'weibull'.

    date_column_name : str, optional
        Name of column containing date information. If None, the index of
        `df` is used.

    min_years : int, optional
        Minimum number of years of data required to calculate percentile
        thresholds for a given day of year. Default is 10.

    **kwargs : dict, optional
        Additional keyword arguments to pass to `numpy.percentile`.

    Returns
    -------
    percentiles : pandas.DataFrame
        DataFrame containing threshold percentiles of data by day of year.

    Examples
    --------
    Calculate default thresholds by day of year from some real data in
    preparation for plotting.

    .. doctest::
        :skipif: True  # dataretrieval functions break CI pipeline

        >>> df, _ = dataretrieval.nwis.get_dv(
        ...     "03586500", parameterCd="00060",
        ...     start="1776-01-01", end="2022-12-31")
        >>> results = percentiles.calculate_fixed_percentile_thresholds_by_day(
        ...     df, "00060_Mean")
        >>> len(results.index)  # 366 days in a leap year
        366
        >>> len(results.columns)  # 8 default percentiles
        8
    """
    # based on date, get min and max day of year available
    if date_column_name is None:
        min_day = df.index.dayofyear.min()
        max_day = df.index.dayofyear.max() + 1
    else:
        min_day = df[date_column_name].dt.dayofyear.min()
        max_day = df[date_column_name].dt.dayofyear.max() + 1
    # make temporal index
    t_idx = np.arange(min_day, max_day)
    # initialize a DataFrame to hold percentiles by day of year
    percentiles_by_day = pd.DataFrame(index=t_idx, columns=percentiles)
    # loop through days of year available
    for doy in range(min_day, max_day):
        # get historical data for the day of year
        data = filter_data_by_time(df, doy, data_column_name,
                                   date_column_name=date_column_name)
        # could insert other functions here to check or modify data
        # as needed or based on any other criteria
        meta = calculate_metadata(data)

        # only calculate data if there are at least min_years of data
        if meta['n_years'] >= min_years:
            # calculate percentiles for the day of year and add to DataFrame
            percentiles_by_day.loc[t_idx == doy, :] = \
                calculate_fixed_percentile_thresholds(
                data, percentiles=percentiles, method=method, **kwargs)
        else:
            # if there are not at least 10 years of data,
            # set percentiles to NaN
            percentiles_by_day.loc[t_idx == doy, :] = np.nan

    # return percentiles by day of year
    return percentiles_by_day
