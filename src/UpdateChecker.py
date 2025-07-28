import requests
import Constants
from tkinter import messagebox
import logging
import version
from version import __version__
from packaging import version
import webbrowser

LOGGER = logging.getLogger(__name__)

def check_for_updates():
    try:
        response = requests.get(f"https://api.github.com/repos/{Constants.GITHUB_REPO}/releases/latest")
        response.raise_for_status()
        latest_release = response.json()
        latest_version = latest_release["tag_name"]  # e.g., "v1.8.0"
        download_url = latest_release["html_url"]

        current_version_parsed = version.parse(__version__)
        new_version_parsed = version.parse(latest_version.lstrip("v"))         #strip "v" from the tag for comparison

        LOGGER.info(f"Current version: {current_version_parsed}, Latest version: {new_version_parsed}")

        if current_version_parsed < new_version_parsed:
            if messagebox.askyesno(
                "Update Available",
                f"A new version ({latest_version}) is available (Current version is {__version__}). Would you like to download it?"
            ):
                webbrowser.open(download_url)

        #TODO: Could potentially stored last version checked somewhere so that we don't ask every time if user reply no. Would need a new menu item for that to force update tho.

    except Exception as e:
        LOGGER.error(f"Failed to check for updates: {e}")