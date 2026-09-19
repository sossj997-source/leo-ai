import os
import subprocess
import shutil


# ==================================================
# OPEN APPLICATION
# ==================================================

def open_app(
    app_name: str
) -> str:
    """
    Open a Windows application.

    Examples:
        notepad
        calculator
        calc
        mspaint
    """

    if not app_name or not app_name.strip():
        raise ValueError(
            "Application name cannot be empty."
        )

    app_name = app_name.strip()

    # ----------------------------------------------
    # Safe built-in Windows applications
    # ----------------------------------------------

    known_apps = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "calc": "calc.exe",
        "paint": "mspaint.exe",
        "mspaint": "mspaint.exe",
        "wordpad": "write.exe",
    }

    executable = known_apps.get(
        app_name.lower()
    )

    # ----------------------------------------------
    # Known application
    # ----------------------------------------------

    if executable:

        try:

            subprocess.Popen(
                [executable],
                shell=False
            )

            return (
                f"Opened {app_name} successfully."
            )

        except Exception as e:

            raise RuntimeError(
                f"Could not open {app_name}: {e}"
            ) from e

    # ----------------------------------------------
    # Try executable available in PATH
    # ----------------------------------------------

    executable_path = shutil.which(
        app_name
    )

    if executable_path:

        try:

            subprocess.Popen(
                [executable_path],
                shell=False
            )

            return (
                f"Opened {app_name} successfully."
            )

        except Exception as e:

            raise RuntimeError(
                f"Could not open {app_name}: {e}"
            ) from e

    raise ValueError(
        f"I couldn't find the application "
        f"'{app_name}'."
    )