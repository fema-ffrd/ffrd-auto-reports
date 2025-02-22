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
import s3fs
from urllib.parse import urlparse
import streamlit as st
from dotenv import load_dotenv

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


def initialize_session(root_directory: str, session_type: str):
    """
    When app is first opened or browser refreshed reset the session info and
    make required folders

    Parameters
    ----------
    root_directory : str
        The root directory of the application
    session_type : str
        The type of session to initialize. Either 'dev' or 'prod'

    Returns
    -------
    None
    """
    if session_type == "dev":
      load_dotenv(".env")
      os.environ["STREAMLIT_SERVER_MAX_UPLOAD_SIZE"] = os.getenv(
          "STREAMLIT_SERVER_MAX_UPLOAD_SIZE"
      )
      os.environ["STREAMLIT_SERVER_RUN_ON_SAVE"] = os.getenv(
          "STREAMLIT_SERVER_RUN_ON_SAVE"
      )
      os.environ["STREAMLIT_THEME_PRIMARY_COLOR"] = os.getenv(
          "STREAMLIT_THEME_PRIMARY_COLOR"
      )
    else:
      # load secrets from streamlit secrets
      os.environ["AWS_ACCESS_KEY_ID"] = st.secrets["AWS_ACCESS_KEY_ID"]
      os.environ["AWS_SECRET_ACCESS_KEY"] = st.secrets["AWS_SECRET_ACCESS_KEY"]
      os.environ["STREAMLIT_THEME_PRIMARY_COLOR"] = st.secrets["STREAMLIT_THEME_PRIMARY_COLOR"]

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
            if folder != "test":
                folder_date = datetime.strptime(folder, "%Y_%b_%d_%H_%M_%S_%f")
                if (datetime.now() - folder_date).days > 1:
                    print(f"Deleting old session data directory: {folder}")
                    shutil.rmtree(folder_path)
            else:
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
    st.session_state["figure_generated"] = False


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

def list_s3_files(s3_uri: str, file_type: str):
    """
    List all files within an s3 folder given a file in the folder.

    Args:
        s3_uri (str): The S3 URI of a bucket (e.g., 's3://my-bucket/my-folder').
        file_type (str): The file type to filter for. One of "g" or "p".

    Returns:
        plan_files: A list of plan file extensions in the S3 URI folder.
    """

    # Parse the S3 URI
    parsed_url = urlparse(s3_uri)
    bucket_name = parsed_url.netloc
    prefix = parsed_url.path.lstrip('/')

    # Create an S3 filesystem object
    fs = s3fs.S3FileSystem()

    # List objects within the specified prefix
    file_keys = fs.ls(f'{bucket_name}/{prefix}', detail=False)

    # filter to only include files with .hdf extensions
    file_keys = [file for file in file_keys if file.endswith(".hdf")]

    # filter to only include hdf files of the specifed type (g or p)
    hdf_files = []
    for file in file_keys:
        if file.endswith(".hdf"):
            file_extension = file.split("/")[-1].split(".")[-2]
            model_name = file.split("/")[-1].split(".")[-3]
            if file_extension.startswith(file_type):
                available_file = f"{model_name}.{file_extension}.hdf"
                hdf_files.append(available_file)

    return hdf_files

particles_js = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Particles.js</title>
  <style>
  #particles-js {
    position: fixed;
    width: 100vw;
    height: 100vh;
    top: 0;
    left: 0;
    z-index: -1; /* Send the animation to the back */
  }
  .content {
    position: relative;
    z-index: 1;
    color: white;
  }
  
</style>
</head>
<body>
  <div id="particles-js"></div>
  <div class="content">
    <!-- Placeholder for Streamlit content -->
  </div>
  <script src="https://cdn.jsdelivr.net/particles.js/2.0.0/particles.min.js"></script>
  <script>
    particlesJS("particles-js", {
      "particles": {
        "number": {
          "value": 500,
          "density": {
            "enable": true,
            "value_area": 800
          }
        },
        "color": {
          "value": "#0000ff"
        },
        "shape": {
          "type": "circle",
          "stroke": {
            "width": 0,
            "color": "#ffffff"
          },
          "polygon": {
            "nb_sides": 5
          },
          "image": {
            "src": "img/github.svg",
            "width": 100,
            "height": 100
          }
        },
        "opacity": {
          "value": 0.8,
          "random": false,
          "anim": {
            "enable": false,
            "speed": 1,
            "opacity_min": 0.2,
            "sync": false
          }
        },
        "size": {
          "value": 2,
          "random": true,
          "anim": {
            "enable": false,
            "speed": 50,
            "size_min": 0.1,
            "sync": false
          }
        },
        "line_linked": {
          "enable": true,
          "distance": 100,
          "color": "#0000ff",
          "opacity": 0.5,
          "width": 1
        },
        "move": {
          "enable": true,
          "speed": 0.9,
          "direction": "none",
          "random": false,
          "straight": false,
          "out_mode": "out",
          "bounce": true,
          "attract": {
            "enable": false,
            "rotateX": 600,
            "rotateY": 1200
          }
        }
      },
      "interactivity": {
        "detect_on": "canvas",
        "events": {
          "onhover": {
            "enable": true,
            "mode": "grab"
          },
          "onclick": {
            "enable": true,
            "mode": "repulse"
          },
          "resize": true
        },
        "modes": {
          "grab": {
            "distance": 100,
            "line_linked": {
              "opacity": 1
            }
          },
          "bubble": {
            "distance": 400,
            "size": 2,
            "duration": 2,
            "opacity": 0.5,
            "speed": 1
          },
          "repulse": {
            "distance": 200,
            "duration": 0.4
          },
          "push": {
            "particles_nb": 2
          },
          "remove": {
            "particles_nb": 3
          }
        }
      },
      "retina_detect": true
    });
  </script>
</body>
</html>
"""
