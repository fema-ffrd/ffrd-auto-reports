# -*- coding: utf-8 -*-

# Imports #####################################################################

import sys
import os
import asyncio
import numpy as np
import streamlit as st
import warnings

warnings.filterwarnings("ignore")

from app_utilities import initialize_session, list_s3_files

# Determine where the script is located in the Pages folder
currDir = os.path.dirname(os.path.realpath(__file__))
# Shift one level up to the src directory
srcDir = os.path.abspath(os.path.join(currDir, ".."))
# Shift another level up to the local root directory
rootDir = os.path.abspath(os.path.join(srcDir, ".."))
# Define the data directory as the assets folder within the src directory
dataDir = os.path.join(srcDir, "assets")

sys.path.append(srcDir)

from hdf_utils import get_model_perimeter
from hy_river import get_usgs_stations
from figures import plot_hydrographs


# layout options: wide mode, centered mode
st.set_page_config(layout="centered", page_icon="💧")
if __name__ == "__main__":
    # setup a session data when app is first opened or browser reset
    if "session_id" not in st.session_state:
        initialize_session(rootDir)

    session_data_dir = st.session_state["session_data_dir"]
    st.session_state["figure_generated"] = False
    st.title("Plot Hydrographs")
    st.write(
        "Plot each calibrated gage hydrograph within the respective modeled domain."
    )

    st.subheader("Required Input")
    st.write("S3 bucket where the developed HEC-RAS model is stored.")
    S3_BUCKET_PATH = st.text_input(
        "S3 Bucket", "s3://trinity-pilot/Checkpoint1-ModelsForReview/Hydraulics/Denton/Trinity_1203_Denton/",

    )
    if S3_BUCKET_PATH is not None:
        try:
            available_geom_files = list_s3_files(S3_BUCKET_PATH, "g")
            available_plan_files = list_s3_files(S3_BUCKET_PATH, "p")
            # check if there is a / at the end of the bucket
            if S3_BUCKET_PATH[-1] != "/":
                S3_BUCKET_PATH = S3_BUCKET_PATH + "/"
        except Exception as e:
            st.error(f"Error: The provided S3 bucket does not exist. Please verify the correct S3 bucket path.")
            st.stop()
    else:
        available_geom_files = []
        available_plan_files = []

    st.write("Select a single geometry file")
    GEOM_HDF_FILE = st.selectbox(
        label="Geometry HDF File",
        options=available_geom_files
    )
    st.write("Select one or more plan files")
    PLAN_HDF_FILES = st.multiselect(
        label="Plan HDF File(s)",
        options=available_plan_files,
        default=None,
        max_selections=6,
    )
    st.write("Select the hydrograph parameter to plot.")
    HYDRO_PARAM = st.selectbox(
        "Hydrograph Parameter",
        ["Flow", "Stage"],
        index=0,
    )
    st.subheader("Optional Input")
    st.write(
        "The name of the 2D flow area within the HEC-RAS model. Only necessary if more than one 2D flow area is present."
    )
    DOMAIN_ID = st.text_input("Domain ID", None)
    st.write("Filter out old gages or process all available gage data.")
    GAGE_COLLECTION_METHOD = st.radio(
        "Gage Filter Method:",
        [
            "Collect all gages, old and current",
            "Only collect gages that provide current data",
        ],
        index=0,
    )
    if HYDRO_PARAM == "Flow":
        st.write("Select the baseflow separation method.")
        BASEFLOW_METHOD = st.radio(
            "Baseflow Seperation Method:",
            [
                "Eckhardt",
                "Chapman",
                "Chapman & Maxwell",
                "Local",
                "None",
            ],
            index=0,
        )
        if BASEFLOW_METHOD == "Eckhardt":
            st.write("""
                    The Eckhardt method (Eckhardt, 2005) is a recursive digital filter that 
                    separates the baseflow from the total flow. This method is generally
                    considered the most accurate across CONUS based on past research:
                    https://doi.org/10.1016/j.jhydrol.2020.124628
                    
                    The two parameters required for the Eckhardt filter are alpha and beta. 
                        
                    The alpha parameter ( 0 < a < 1) is the recession coefficient, which controls the 
                    responsiveness of the filter and indicates the type of groundwater system. Large 
                    values for a indicate groundwater dominated - slow draining systems. Small values 
                    for a indicate shallow subsurface flow dominated fast draining systems.
                    The recession coefficient is estimated using the gaged period of record for daily
                    streamflow data assuming exponential recession behavior. https://doi.org/10.1016/j.envsoft.2021.104983
                        
                    The beta parameter (0 < b < 1) is the baseflow index, which is the maximum percentage
                    of the total flow that can be attributed to baseflow. The baseflow index for individual 
                    reach catchments of the NHDFPlus version 2 data suite is estimated by the U.S. 
                    Geological Survey's (USGS) National Water-Quality Assessment Project (NAWQA) which is 
                    part of the USGS National Water Quality Program (NWQP). https://doi.org/10.5066/P9PA63SM
                        """)
        elif BASEFLOW_METHOD == "Chapman":
            st.write("""
                    The Chapman method (Chapman, 1991) is a recursive digital filter that separates the baseflow
                    from the total flow. This method is considered less complex and accurate than the Eckhardt 
                    method but it is still widely used. The Chapman method is based on the assumption that the 
                    baseflow is a linear function of the streamflow. Meaning, it assumes that the baseflow can 
                    be modeled as a linear reservoir, where the outflow (baseflow) is proportional to the storage 
                    (groundwater). 
                    
                    The main parameter required for the Chapman filter is alpha.
                     
                    The alpha parameter ( 0 < a < 1) is the recession coefficient, which controls the 
                    responsiveness of the filter and indicates the type of groundwater system. Large 
                    values for a indicate groundwater dominated - slow draining systems. Small values 
                    for a indicate shallow subsurface flow dominated fast draining systems.
                    The recession coefficient is estimated using the gaged period of record for daily
                    streamflow data assuming exponential recession behavior. https://doi.org/10.1016/j.envsoft.2021.104983
                    """)
        elif BASEFLOW_METHOD == "Chapman & Maxwell":
            st.write("""
                    The Chapman & Maxwell method (Chapman & Maxwell, 1996) is a recursive digital filter that 
                    separates the baseflow from the total flow. While the Chapman & Maxwell method uses a similar 
                    formula to the original Chapman method, it incorporates additional considerations to improve 
                    accuracy, particularly in varying hydrological conditions. This makes it more robust for different 
                    types of watersheds and streamflow patterns.
                     
                    The main parameter required for the Chapman filter is alpha.
                     
                    The alpha parameter ( 0 < a < 1) is the recession coefficient, which controls the 
                    responsiveness of the filter and indicates the type of groundwater system. Large 
                    values for a indicate groundwater dominated - slow draining systems. Small values 
                    for a indicate shallow subsurface flow dominated fast draining systems.
                    The recession coefficient is estimated using the gaged period of record for daily
                    streamflow data assuming exponential recession behavior. https://doi.org/10.1016/j.envsoft.2021.104983
                    """)
        elif BASEFLOW_METHOD == "Local":
            st.write("""
                    The Local minimum graphical method from HYSEP program (Sloto & Crouse, 1996) is one of the 
                    three hydrograph separation techniques included in the HYSEP (Hydrograph Separation) 
                    program developed by Ronald A. Sloto and Michèle Y. Crouse in 1996. The method identifies 
                    baseflow by finding the minimum streamflow values over specified intervals.
                     
                    The streamflow hydrograph is divided into ( N )-day intervals, where ( N ) is a user-specified 
                    duration. This interval length is typically chosen based on the watershed’s response time to 
                    precipitation events. Within each ( N )-day interval, the minimum streamflow value is identified. 
                    These local minima are assumed to represent the baseflow component of the streamflow. The 
                    identified local minima are then connected to form a continuous baseflow hydrograph. This 
                    graphical method assumes that the lowest flow values within each interval are primarily 
                    due to groundwater contributions, thus representing baseflow.
                    """)
        elif BASEFLOW_METHOD == "None":
            st.write("""
                    No baseflow separation method will be applied to the hydrograph.
                    """)

    # Create and set an event loop
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # Generate Report
    st.subheader("Generate Figure(s)")
    st.write("Click the button below to generate the figure(s).")
    if st.button("Begin Figure Generation"):
        if GEOM_HDF_FILE is not None and PLAN_HDF_FILES is not None:
            # Construct the full path to each plan hdf file
            GEOM_HDF_PATH = S3_BUCKET_PATH + GEOM_HDF_FILE
            PLAN_HDF_PATHS = [S3_BUCKET_PATH + file for file in PLAN_HDF_FILES]
            # Get the model perimeter and domain name
            model_perimeter = get_model_perimeter(
                GEOM_HDF_PATH, DOMAIN_ID, project_to_4326=True
            )
            domain_name = model_perimeter["mesh_name"].values[0]
            # Acquire all USGS gages within the model perimeter
            df_gages_usgs = get_usgs_stations(model_perimeter, "flow", None)
            if GAGE_COLLECTION_METHOD == "Only collect gages that provide current data":
                end_date = df_gages_usgs.end_date.max().strftime("%Y-%m-%d")
                df_gages_usgs = df_gages_usgs[df_gages_usgs["end_date"] == end_date]
            else:
                pass
            plan_img_dict = {}
            plan_metrics_dict = {}
            for plan_index, plan in enumerate(PLAN_HDF_PATHS):
                # Plot the calibrated gage hydrographs
                plan_index = plan_index + 1
                imgs_dict, metrics_df = plot_hydrographs(
                    plan,
                    model_perimeter,
                    df_gages_usgs,
                    HYDRO_PARAM,
                    BASEFLOW_METHOD,
                    domain_name,
                    session_data_dir,
                    plan_index,
                    report_document=None,
                    report_keywords=None,
                )
                plan_img_dict[plan] = imgs_dict
                plan_metrics_dict[plan] = metrics_df

                if len(imgs_dict) == 0:
                    st.error("No gages were found within the model perimeter.")
                else:
                    st.success("Figure(s) generated successfully!")
                    st.session_state["figure_generated"] = True
        else:
            st.error("Please provide the required input.")

    if st.session_state["figure_generated"]:
        gage_idx, plan_idx = 0, 0
        for plan in PLAN_HDF_PATHS:
            plan_idx = plan_idx + 1
            # Display the metrics
            st.dataframe(plan_metrics_dict[plan].T)
            # Display the figures. Key is the unique gage name: USGS-08087000
            for key in plan_img_dict[plan].keys():
                gage_idx = gage_idx + 1
                img_path = plan_img_dict[plan][key]
                # Read the image file in binary mode
                with open(img_path, "rb") as file:
                    btn = st.download_button(
                        label="Click here to download the figure",
                        data=file,
                        file_name=f"plan0{plan_idx}_gage0{gage_idx}.png",
                        mime="image/png"
                    )
                st.image(img_path)
