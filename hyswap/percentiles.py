"""Percentile calculation functions."""

import numpy as np
import pandas as pd
from hyswap.utils import filter_data_by_time
from hyswap.utils import calculate_metadata
from hyswap.utils import define_year_doy_columns
from hyswap.utils import set_data_type
from hyswap.utils import rolling_average


def calculate_fixed_percentile_thresholds(
        data,
        percentiles=np.array((0, 5, 10, 25, 75, 90, 95, 100)),
        method='weibull',
        ignore_na=True,
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

    ignore_na : bool, optional
        Ignore NA values in percentile calculations

    **kwargs : dict, optional
        Additional keyword arguments to pass to `numpy.percentile`.

    Returns
    -------
    percentiles : pandas.DataFrame
        Percentiles of the data in a DataFrame so the thresholds and
        percentile values are tied together.

    Examples
    --------
    Calculate default percentile thresholds from some synthetic data.

    .. doctest::

        >>> data = np.arange(101)
        >>> results = percentiles.calculate_fixed_percentile_thresholds(
        ...     data, method='linear')
        >>> results
        thresholds  0    5     10    25    75    90    95     100
        values      0.0  5.0  10.0  25.0  75.0  90.0  95.0  100.0

    Calculate a different set of thresholds from some synthetic data.

    .. doctest::

        >>> data = np.arange(101)
        >>> results = percentiles.calculate_fixed_percentile_thresholds(
        ...     data, percentiles=np.array((0, 10, 50, 90, 100)))
        >>> results
        thresholds  0    10    50    90     100
        values      0.0  9.2  50.0  90.8  100.0
    """
    if ignore_na:
        pct = np.nanpercentile(data, percentiles, method=method, **kwargs)
    else:
        pct = np.percentile(data, percentiles, method=method, **kwargs)
    df = pd.DataFrame(data={"values": pct}, index=percentiles).T
    df = df.rename_axis("thresholds", axis="columns")
    return df


def calculate_variable_percentile_thresholds_by_day(
        df,
        data_column_name,
        percentiles=[0, 5, 10, 25, 75, 90, 95, 100],
        method='weibull',
        date_column_name=None,
        data_type='daily',
        year_type='calendar',
        min_years=10,
        leading_values=0,
        trailing_values=0,
        ignore_na=True,
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

    data_type : str, optional
        The type of data. Must be one of 'daily', '7-day', '14-day', and
        '28-day'. Default is 'daily'. If '7-day', '14-day', or '28-day' is
        specified, the data will be averaged over the specified period. NaN
        values will be used for any days that do not have data. If present,
        NaN values will result in NaN values for the entire period.

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

    leading_values : int, optional
        For the temporal filtering, this is an argument setting the
        number of leading values to include in the output, inclusive.
        Default is 0, and parameter only applies to 'day' time_interval.

    trailing_values : int, optional
        For the temporal filtering, this is an argument setting the
        number of trailing values to include in the output, inclusive.
        Default is 0, and parameter only applies to 'day' time_interval.

    ignore_na : bool, optional
        Ignore NA values in percentile calculations

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
    # define year and day of year columns and convert date column to datetime
    # if necessary
    df = define_year_doy_columns(df, date_column_name=date_column_name,
                                 year_type=year_type, clip_leap_day=True)
    # do rolling average for time as needed
    data_type = set_data_type(data_type)
    df = rolling_average(df, data_column_name, data_type)
    # based on date, get min and max day of year available
    min_day = np.nanmax((1, df.index.dayofyear.min()))
    max_day = np.nanmin((366, df.index.dayofyear.max() + 1))
    # make temporal index
    t_idx = np.arange(min_day, max_day)
    # initialize a DataFrame to hold percentiles by day of year
    percentiles_by_day = pd.DataFrame(index=t_idx, columns=percentiles)
    # loop through days of year available
    for doy in range(min_day, max_day):
        # get historical data for the day of year
        data = filter_data_by_time(df, doy, data_column_name,
                                   leading_values=leading_values,
                                   trailing_values=trailing_values,
                                   drop_na=ignore_na)
        # could insert other functions here to check or modify data
        # as needed or based on any other criteria
        meta = calculate_metadata(data)

        # only calculate data if there are at least min_years of data
        if meta['n_years'] >= min_years:
            # calculate percentiles for the day of year and add to DataFrame
            _pct = calculate_fixed_percentile_thresholds(
                    data, percentiles=percentiles, method=method, 
                    ignore_na=ignore_na, **kwargs)
            percentiles_by_day.loc[t_idx == doy, :] = _pct.values.tolist()[0]
        else:
            # if there are not at least 10 years of data,
            # set percentiles to NaN
            percentiles_by_day.loc[t_idx == doy, :] = np.nan

    # replace index with multi-index of doy_index and month-day values
    # month_day values
    month_day = pd.to_datetime(
        percentiles_by_day.index, format='%j').strftime('%m-%d')
    # doy_index values
    doy_index = percentiles_by_day.index.values
    if year_type == 'water':
        doy_index = doy_index - 273
        doy_index[doy_index < 1] += 365
    elif year_type == 'climate':
        doy_index = doy_index - 90
        doy_index[doy_index < 1] += 365
    percentiles_by_day.index = pd.MultiIndex.from_arrays(
        [doy_index, month_day], names=['doy', 'month-day'])

    # sort percentiles by index
    percentiles_by_day.sort_index(inplace=True)

    # return percentiles by day of year
    return percentiles_by_day


def calculate_percentile_from_value(value, percentile_df):
    """Calculate percentile from a value and existing percentile values.

    This function enables faster calculation of the percentile associated with
    a given value if percentile values and corresponding percentiles are known
    for other data from the same station or site. This calculation is done
    using linear interpolation.

    Parameters
    ----------
    value : float, np.ndarray
        New value(s) to calculate percentile for. Can be a single value or an
        array of values.

    percentile_df : pd.DataFrame
        DataFrame where columns are the percentile thresholds values and the
        values are stored in a row called "values". Typically generated by the
        `calculate_fixed_percentile_thresholds` functions but could be
        provided manually or from data pulled from the NWIS stats service.

    Returns
    -------
    percentile : float, np.ndarray
        Percentile associated with the input value(s).

    Examples
    --------
    Calculate the percentile associated with a value from some synthetic data.

    .. doctest::

        >>> data = np.arange(101)
        >>> pcts_df = percentiles.calculate_fixed_percentile_thresholds(
        ...     data, percentiles=[0, 5, 10, 25, 75, 90, 95, 100],
        ...     method='linear')
        >>> new_percentile = percentiles.calculate_percentile_from_value(
        ...     51, pcts_df)
        >>> new_percentile
        51.0
    """
    # define values
    thresholds = percentile_df.columns.tolist()
    percentile_values = percentile_df.values.tolist()[0]
    # do and return linear interpolation
    return np.interp(value, percentile_values, thresholds)
