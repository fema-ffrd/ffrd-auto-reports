# -*- coding: utf-8 -*-

# Script Description ##########################################################
"""
Utility functions for the MBI-DAA web application
"""
# Imports #####################################################################

import os
import shutil
from datetime import datetime
import zipfile
import streamlit as st

# Functions ###################################################################


def remove_all_folders(directory):
    """
    Remove all files and folders within a directory

    Parameters
    ----------
    directory : str
        Path to the directory to remove all files and folders from

    Returns
    -------
    None
    """
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.path.isdir(file_path):
            shutil.rmtree(file_path)


def initialize_session(root_directory: str):
    """
    When app is first opened or browser refreshed reset the session info and
    make required folders

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    # Capture the timestamp of the session: year_month_day_hour_minute_second_microsecond
    st.session_state["session_id"] = datetime.now()
    # Assign the timestamp to a string variable for the session id
    session_id_str = st.session_state["session_id"].strftime("%Y_%b_%d_%H_%M_%S_%f")
    # Create the session directory and data subfolder per session
    os.makedirs(
        os.path.join(root_directory, "session", session_id_str, "data"), exist_ok=True
    )
    session_dir = os.path.join(root_directory, "session")
    session_data_dir = os.path.join(session_dir, session_id_str, "data")

    # Delete session data directories older than 1 day
    for folder in os.listdir(session_dir):
        folder_path = os.path.join(session_dir, folder)
        if os.path.isdir(folder_path):
            folder_date = datetime.strptime(folder, "%Y_%b_%d_%H_%M_%S_%f")
            if (datetime.now() - folder_date).days > 1:
                print(f"Deleting old session data directory: {folder}")
                shutil.rmtree(folder_path)

    # if session data directory does not exist, create it
    if not os.path.exists(session_data_dir):
        # parent directory for user session
        os.makedirs(session_data_dir)

    # set session data
    st.session_state["session_id_str"] = session_id_str
    st.session_state["session_data_dir"] = session_data_dir
    st.session_state["selected_method"] = None
    st.session_state["data_acquired"] = False
    st.session_state["request_zip"] = False
    st.session_state["login_success"] = False


def compress_directory(data_directory: str, output_zip_file: str):
    with zipfile.ZipFile(output_zip_file, "a") as zf:
        for dirname, subdirs, files in os.walk(data_directory):
            for filename in files:
                zf.write(os.path.join(dirname, filename))
    zf.close()

    return output_zip_file


def write_session_parameters(session_state):
    """write current session parameters to a csv. assumes
    "session_id_str" and "session_data_dir" are keys in session state
    for naming and output location.

    Args:
        session_state (streamlit object): should pass 'st.session_state'
    Returns
        None

    """
    # get csv location from session state parameters
    output_csv = os.path.join(
        session_state["session_data_dir"],
        f"session_parameters_{session_state['session_id_str']}.csv",
    )

    # write session state parameters to csv
    with open(output_csv, "w") as f:
        for key in session_state.keys():
            # f.write("%s,%s\n"%(key,my_dict[key]))
            f.write(f"{key},{session_state[key]}\n")
