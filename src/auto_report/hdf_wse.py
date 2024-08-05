# -*- coding: utf-8 -*-

# Imports #####################################################################

import os
import warnings
import h5py
import fsspec
import pandas as pd
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")

# assign a global font size for the plots
plt.rcParams.update({"font.size": 16})

# Functions ###################################################################


def calc_scenario_stats(df: pd.DataFrame, target_column: str):
    """ "
    Calculate the frequency, PDF, and CDF of a target column in a dataframe

    Parameters
    ----------
    df : pd.DataFrame
        A pandas dataframe with the target column
    target_column : str
        The name of the target column in the dataframe

    Returns
    -------
    stats_df : pd.DataFrame
        A pandas dataframe with the frequency, PDF, and CDF of the target column
    """
    # filter out values of -9999 and zeros
    df = df[df[target_column] != -9999]
    df = df[df[target_column] > 0]
    # Frequency
    stats_df = (
        df.groupby(target_column)[target_column]
        .agg("count")
        .pipe(pd.DataFrame)
        .rename(columns={target_column: "frequency"})
    )
    # PDF
    stats_df["pdf"] = stats_df["frequency"] / sum(stats_df["frequency"])
    # CDF
    stats_df["cdf"] = stats_df["pdf"].cumsum() * 100
    stats_df = stats_df.reset_index()
    return stats_df


def plot_hist_cdf(
    stats_df: pd.DataFrame,
    target_column: str,
    plot_title: str,
    threshold: float,
    num_bins: int,
    output_path: str,
):
    """
    Plot a histogram and CDF of a target column in a dataframe

    Parameters
    ----------
    stats_df : pd.DataFrame
        A pandas dataframe with the frequency, PDF, and CDF of the target column
    target_column : str
        The name of the target column in the dataframe
    plot_title : str
        The title of the plot
    threshold : float
        The threshold for the histogram's x-axis
    num_bins : int
        The number of bins for the histogram
    output_path : str
        The path to save the plot
    """

    fig, ax = plt.subplots(2, 1, sharex=True, figsize=(10, 10))
    ax = ax.flatten()
    # plot the histogram
    target_values = stats_df[target_column].values
    filtered_values = target_values[(target_values <= threshold) & (target_values >= 0)]
    weights = np.ones_like(filtered_values) / float(len(filtered_values)) * 100
    n, bins, patches = ax[0].hist(
        filtered_values,
        bins=num_bins,
        weights=weights,
        range=(0, threshold),
        density=False,
    )
    # determine the percentage of cells that have errors greater than the threshold
    if target_column == "ttp_hrs":
        # cells with time to peak occuring within the last hour of the simulation
        exceedance = int(len(target_values[target_values >= threshold]))
        plot_units = "hours"
    else:
        # cells with WSE errors greater than the threshold
        exceedance = int(len(target_values[(target_values > threshold)]))
        plot_units = "ft"

    ax[0].set(
        xlabel=f"{plot_title} ({plot_units})",
        ylabel="Cell Count (%)",
        title=f"Histogram: n bins = {num_bins}",
    )
    ax[0].set_xlim(0, threshold)
    ax[0].grid()
    # add a legend
    if target_column == "ttp_hrs":
        ax[0].legend(
            [f"{plot_title} >= {threshold:.0f}: {exceedance} Cells"], loc="upper right"
        )
    else:
        ax[0].legend(
            [f"{plot_title} > {threshold:.1f}: {exceedance} Cells"], loc="upper right"
        )

    # plot the CDF
    cdf_df = stats_df[
        (stats_df[target_column] <= threshold) & (stats_df[target_column] >= 0)
    ]
    # Resample the data to num_bins equally spaced points
    x = np.linspace(cdf_df[target_column].min(), cdf_df[target_column].max(), num_bins)
    y = np.interp(
        x, cdf_df[target_column].sort_values(), np.linspace(0, 100, len(cdf_df))
    )
    cdf_df = pd.DataFrame({target_column: x, "cdf": y})

    ax[1].plot(cdf_df[target_column], cdf_df["cdf"], linewidth=3)
    ax[1].set(
        xlabel=f"{plot_title} ({plot_units})",
        ylabel="P(X <= x) (%)",
        title="Non-Exceedance Probability",
    )
    ax[1].set_xlim(0, threshold)
    ax[1].set_ylim(0, 100)
    ax[1].grid()
    if target_column == "ttp_hrs":
        ax[1].xaxis.set_major_formatter(
            plt.FuncFormatter(lambda x, _: "{:.0f}".format(x))
        )
    else:
        ax[1].xaxis.set_major_formatter(
            plt.FuncFormatter(lambda x, _: "{:.2f}".format(x))
        )
    # add space between both subplots
    plt.tight_layout()
    # save the plot
    plt.savefig(output_path)
    plt.close(fig)


def wse_error_qc(
    cell_points_gdf: gpd.GeoDataFrame,
    wse_error_threshold: float,
    num_bins: int,
    output_path: str,
):
    """
    Read the Max WSE Errors from an HDF file and calculate the CDF and PDF

    Parameters
    ----------
    cell_points_gdf : gpd.GeoDataFrame
        A geopandas dataframe with the geometry of the computational cells
    wse_error_threshold : float
        The threshold for the histogram's x-axis
    num_bins : int
        The number of bins for the histogram
    output_path : str
        The path to save the plot

    Returns
    -------
    bool
        True if the max WSE errors were processed successfully, False
    """
    # Process Max WSE Errors and export graphics
    print("Processing Max WSE Errors...")
    if len(cell_points_gdf) == 0:
        print("No cells found in the HDF file")
        return False
    elif len(cell_points_gdf[cell_points_gdf["max_ws_err"] > 0]) == 0:
        print("No cells with WSE errors greater than zero")
        return False
    else:
        # Calculate the frequency, PDF, and CDF of the max WSE errors
        cell_stats_df = calc_scenario_stats(cell_points_gdf, "max_ws_err")
        # Plot the histogram and CDF of the max WSE errors
        plot_hist_cdf(
            cell_stats_df,
            "max_ws_err",
            "Max WSE Error",
            wse_error_threshold,
            num_bins,
            output_path,
        )
        return True


def wse_ttp_qc(cell_points_gdf: gpd.GeoDataFrame, num_bins: int, output_path: str):
    """
    Read the water surface elevations from an HDF file and calculate the time to peak

    Parameters
    ----------
    cell_points_gdf : gpd.GeoDataFrame
        A geopandas dataframe with the geometry of the computational cells
    num_bins : int
        The number of bins for the histogram
    output_path : str
        The path to save the plot

    Returns
    -------
    bool
        True if the time to peak was processed successfully, False otherwise
    """
    # Process WSE time to peak
    print("Processing WSE Time to Peak...")
    if len(cell_points_gdf) == 0:
        print("No cells found in the HDF file")
        return False

    # Determine the global min time to peak for the simulation start time
    start_time = cell_points_gdf["min_ws_time"].min()
    # find the time to peak between the max and min water surface elevation times
    ttp = cell_points_gdf["max_ws_time"] - start_time
    # convert to hours
    ttp = ttp.dt.total_seconds() / 3600
    ttp = ttp.to_frame()
    ttp.columns = ["ttp_hrs"]

    if len(ttp[ttp["ttp_hrs"] > 0]) == 0:
        print("No cells with time to peak greater than zero")
        return False
    else:
        # Define the global max time to peak
        ttp_max = ttp["ttp_hrs"].max()
        cell_points_gdf = None
        # Calculate the frequency, PDF, and CDF of the time to peak
        cell_stats_df = calc_scenario_stats(ttp, "ttp_hrs")
        # Plot the histogram and CDF of the time to peak
        plot_hist_cdf(
            cell_stats_df,
            "ttp_hrs",
            "Time to Peak",
            ttp_max,
            num_bins,
            output_path,
        )
        return True
