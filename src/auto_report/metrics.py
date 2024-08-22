# -*- coding: utf-8 -*-

# Imports #####################################################################

import pandas as pd
import numpy as np
from permetrics.regression import RegressionMetric

# Functions ###################################################################

def pbias_score(obs_values: np.array, model_values: np.array):
    """
    Calculate the Percent Bias

    Parameters
    ----------
    obs_df : pandas dataframe
        Dataframe of observed streamflow data
    model_df : pandas dataframe
        Dataframe of modeled streamflow data
    Returns
    -------
    pbias : float
        Percent Bias
    """
    # calculate the standard deviation of the observed values
    obs_sum = np.sum(obs_values)
    if obs_sum == 0:
        return np.nan
    # calculate the root mean squared error
    diff_sum = np.sum(obs_values - model_values)
    # calculate the root mean standard deviation ratio
    pbias_val = abs(diff_sum / obs_sum)
    pbias_val = pbias_val * 100
    return pbias_val

def calc_metrics(q_df: pd.DataFrame, station_id: str):
    """
    Calculate streamflow statistics

    Parameters
    ----------
    q_df : pandas dataframe
        Dataframe containing observed and modeled streamflow data
    station_id: str
        String unique identified for USGS gage
    
    Returns
    -------
    stats_df : pandas dataframe
        Dataframe of streamflow calibration statistics. Columns are the plan column id and the rows are the statistics
    """
    # create a regression metric object
    evaluator = RegressionMetric(
        y_true=q_df["Observed"].values.reshape(-1, 1),
        y_pred=q_df["Modeled"].values.reshape(-1, 1),
    )
    # calculate the r2
    r2_val = evaluator.R2()
    # calculate the nse
    nse_val = evaluator.nash_sutcliffe_efficiency()
    # calculate the rmse
    rmse_val = evaluator.root_mean_squared_error()
    # calculate the std dev
    std_dev_obs = np.std(q_df["Observed"].values)
    # calculate the rsr
    rsr_val = rmse_val / std_dev_obs
    # calculate the pbias
    pbias_val = pbias_score(q_df["Observed"].values, q_df["Modeled"].values)
    # compile the statistics into a dataframe
    stats_df = pd.DataFrame(
        {
            "R2": [r2_val],
            "NSE": [nse_val],
            "RSR": [rsr_val],
            "PBIAS": [pbias_val],
        }
    )
    stats_df.index = [station_id]
    return stats_df
