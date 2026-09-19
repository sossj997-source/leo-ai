import os
import subprocess
from pathlib import Path


# =========================================================
# COMMON PATH HELPERS
# =========================================================

def _get_desktop() -> Path:
    return Path.home() / "Desktop"


def _get_downloads() -> Path:
    return Path.home() / "Downloads"


def _resolve_special_folder(folder_name: str) -> Path:
    """
    Convert common folder names into actual Windows paths.
    """

    if not folder_name or not folder_name.strip():
        raise ValueError("Folder name cannot be empty.")

    name = folder_name.strip().lower()

    special_folders = {
        "desktop": _get_desktop(),
        "downloads": _get_downloads(),
        "download": _get_downloads(),
        "documents": Path.home() / "Documents",
        "documents folder": Path.home() / "Documents",
        "pictures": Path.home() / "Pictures",
        "pictures folder": Path.home() / "Pictures",
        "music": Path.home() / "Music",
        "videos": Path.home() / "Videos",
    }

    if name in special_folders:
        return special_folders[name]

    path = Path(folder_name).expanduser()

    if path.is_absolute():
        return path

    # Try relative to Desktop first
    desktop_path = _get_desktop() / folder_name

    if desktop_path.exists():
        return desktop_path

    # Then current working directory
    current_path = Path.cwd() / folder_name

    if current_path.exists():
        return current_path

    return path


# =========================================================
# OPEN FOLDER
# =========================================================

def open_folder(folder_name: str) -> str:
    """
    Open a folder in Windows File Explorer.
    """

    folder_path = _resolve_special_folder(folder_name)

    if not folder_path.exists():
        raise ValueError(
            f"I couldn't find the folder '{folder_name}'."
        )

    if not folder_path.is_dir():
        raise ValueError(
            f"'{folder_name}' is not a folder."
        )

    try:
        os.startfile(str(folder_path))

        return (
            f"Opened folder '{folder_name}' successfully."
        )

    except Exception as e:
        raise RuntimeError(
            f"Could not open folder '{folder_name}': {e}"
        ) from e


# =========================================================
# LIST FILES
# =========================================================

def list_files(folder_name: str = "Downloads"):
    """
    List files and folders inside a directory.
    """

    folder_path = _resolve_special_folder(folder_name)

    if not folder_path.exists():
        raise ValueError(
            f"I couldn't find the folder '{folder_name}'."
        )

    if not folder_path.is_dir():
        raise ValueError(
            f"'{folder_name}' is not a folder."
        )

    try:
        items = []

        for item in folder_path.iterdir():

            item_type = "folder" if item.is_dir() else "file"

            items.append(
                {
                    "name": item.name,
                    "type": item_type,
                }
            )

        items.sort(
            key=lambda x: (
                x["type"] != "folder",
                x["name"].lower(),
            )
        )

        return {
            "folder": str(folder_path),
            "count": len(items),
            "items": items,
        }

    except Exception as e:
        raise RuntimeError(
            f"Could not list files: {e}"
        ) from e


# =========================================================
# CREATE FOLDER
# =========================================================

def create_folder(
    folder_name: str,
    location: str = "Desktop",
) -> str:
    """
    Create a new folder.
    """

    if not folder_name or not folder_name.strip():
        raise ValueError(
            "Folder name cannot be empty."
        )

    folder_name = folder_name.strip()

    # Basic protection against invalid Windows paths
    invalid_chars = '<>:"/\\|?*'

    if any(char in folder_name for char in invalid_chars):
        raise ValueError(
            "Folder name contains invalid Windows characters."
        )

    parent_path = _resolve_special_folder(location)

    if not parent_path.exists():
        raise ValueError(
            f"Location '{location}' does not exist."
        )

    if not parent_path.is_dir():
        raise ValueError(
            f"Location '{location}' is not a folder."
        )

    new_folder = parent_path / folder_name

    if new_folder.exists():
        raise ValueError(
            f"Folder '{folder_name}' already exists."
        )

    try:
        new_folder.mkdir(
            parents=False,
            exist_ok=False,
        )

        return (
            f"Created folder '{folder_name}' "
            f"inside '{location}'."
        )

    except Exception as e:
        raise RuntimeError(
            f"Could not create folder: {e}"
        ) from e


# =========================================================
# FIND FILE
# =========================================================

def find_file(
    file_name: str,
    search_folder: str = "Downloads",
):
    """
    Search for a file/folder by name.
    """

    if not file_name or not file_name.strip():
        raise ValueError(
            "File name cannot be empty."
        )

    file_name = file_name.strip()

    search_path = _resolve_special_folder(
        search_folder
    )

    if not search_path.exists():
        raise ValueError(
            f"I couldn't find the folder '{search_folder}'."
        )

    if not search_path.is_dir():
        raise ValueError(
            f"'{search_folder}' is not a folder."
        )

    matches = []

    try:
        for root, dirs, files in os.walk(search_path):

            for name in files + dirs:

                if name.lower() == file_name.lower():

                    full_path = Path(root) / name

                    matches.append(
                        {
                            "name": name,
                            "path": str(full_path),
                            "type": (
                                "folder"
                                if full_path.is_dir()
                                else "file"
                            ),
                        }
                    )

        return {
            "search_folder": str(search_path),
            "file_name": file_name,
            "count": len(matches),
            "matches": matches,
        }

    except Exception as e:
        raise RuntimeError(
            f"File search failed: {e}"
        ) from e


# =========================================================
# OPEN FILE
# =========================================================

def open_file(file_path: str) -> str:
    """
    Open a file using its default Windows application.
    """

    if not file_path or not file_path.strip():
        raise ValueError(
            "File path cannot be empty."
        )

    path = Path(file_path).expanduser()

    if not path.exists():
        raise ValueError(
            f"I couldn't find the file '{file_path}'."
        )

    if not path.is_file():
        raise ValueError(
            f"'{file_path}' is not a file."
        )

    try:
        os.startfile(str(path))

        return (
            f"Opened file '{path.name}' successfully."
        )

    except Exception as e:
        raise RuntimeError(
            f"Could not open file: {e}"
        ) from e