"""Percentile calculation functions."""

import numpy as np
import pandas as pd
from hyswap.utils import filter_data_by_time
from hyswap.utils import calculate_metadata
from hyswap.utils import adjust_doy_for_water_year
from hyswap.utils import adjust_doy_for_climate_year


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
        percentiles=[0, 5, 10, 25, 75, 90, 95, 100],
        method='weibull',
        date_column_name=None,
        year_type='calendar',
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
        [0, 5, 10, 25, 75, 90, 95, 100].

    method : str, optional
        Method to use to calculate percentiles. Default is 'weibull'.

    date_column_name : str, optional
        Name of column containing date information. If None, the index of
        `df` is used.

    year_type : str, optional
        The type of year to use. Must be one of 'calendar', 'water', or
        'climate'. Default is 'calendar' which starts the year on January 1
        and ends on December 31. 'water' starts the year on October 1 and
        ends on September 30 of the following year which is the "water year".
        For example, October 1, 2010 to September 30, 2011 is "water year
        2011". 'climate' years begin on April 1 and end on March 31 of the
        following year, they are numbered by the ending year. For example,
        April 1, 2010 to March 31, 2011 is "climate year 2011".

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
        >>> results = percentiles.calculate_variable_percentile_thresholds_by_day(  # noqa: E501
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
    # adjust for water or climate year if needed
    if (year_type == 'water') or (year_type == 'climate'):
        # make a column of days in the percentiles df
        percentiles_by_day['day'] = percentiles_by_day.index
        # based on size of data frame set index
        min_date = pd.to_datetime('2000-01-01') + \
            pd.DateOffset(days=int(min_day - 1))
        min_date = min_date.strftime('%Y-%m-%d')
        # convert max day of year to YYYY-MM-DD
        max_date = pd.to_datetime('2000-01-01') + pd.DateOffset(
            days=int(min_day + percentiles_by_day.shape[0] - 2))
        max_date = max_date.strftime('%Y-%m-%d')
        # set index to be time from beginning to max_date
        percentiles_by_day.index = pd.date_range(min_date, max_date)
        # do water year adjustment
        if year_type == 'water':
            # do adjustment
            percentiles_by_day = adjust_doy_for_water_year(
                percentiles_by_day, 'day')
        elif year_type == 'climate':
            # do adjustment
            percentiles_by_day = adjust_doy_for_climate_year(
                percentiles_by_day, 'day')
        # use day column to rewrite the index
        percentiles_by_day.index = percentiles_by_day['day']
        # drop the day column
        percentiles_by_day.drop('day', axis=1, inplace=True)
    # return percentiles by day of year
    return percentiles_by_day
