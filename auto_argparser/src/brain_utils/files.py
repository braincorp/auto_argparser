""" Simple file utils """
import os
from datetime import datetime


def mkdir_p(dirname):
    """
    Check if directory exists and if not, make it.
    :param dirname: dir to create / check
    :return str: The full path to the dir
    """
    try:  # More thread-safe than "look before you leap"
        os.makedirs(dirname)
    except OSError:
        pass
    return dirname


def ensure_parent_dir_exists(file_path: str) -> None:
    """ Ensure that the parent directory for the file exists """
    parent_dir, _ = os.path.split(file_path)
    mkdir_p(parent_dir)


def expand_path(*file_path_parts) -> str:
    """
    Expand the user directory and join the parts
    :param file_path_parts: Parts to be joined into file path
    :return: The expanded path that it is definitely save to write to.
    """
    file_path = os.path.join(*file_path_parts)
    file_path = os.path.abspath(os.path.expanduser(file_path))
    return file_path


def ensure_path(*file_path_parts) -> str:
    """ Ensure that the path results in a writable file.  This includes:
    - Expanding ~ into userdir
    - Turning relative paths into absolute paths
    - Ensuring parent dir exists
    :param file_path_parts: Parts to be joined into file path
    :return: The expanded path that it is definitely save to write to.
    """
    file_path = expand_path(*file_path_parts)
    ensure_parent_dir_exists(file_path)
    return file_path


def generate_current_time_folder_name(path_prefix):
    """
    Generates a folder name where the name of the folder is based on the current time
    :param path_prefix str: path to prepend to the generated folder name
    :return str: path of the generated folder name
    """
    time_str = datetime.now().strftime("%Y-%m-%d_%I-%M-%S_%p")
    return os.path.join(path_prefix, time_str)


def generate_current_time_filename(path_prefix, extension):
    """
    Generates a filename where the name of the file is based on the current time and extension
    :param path_prefix str: path to prepend to the generated filename
    :param extension str: file extension of the generated file
    :return str: path of the generated filename
    """
    time_str_file = datetime.now().strftime("%Y-%m-%d_%I-%M-%S_%p.{}".format(extension))
    return os.path.join(path_prefix, time_str_file)


def update_filename_with_current_time(path_prefix: str, extension: str) -> str:
    """
    Generates a filename where the name of the file is updated based on the current time and extension
    :param path_prefix: path to prepend to the generated filename
    :param extension: file extension of the generated file
    :return str: path of the generated filename
    """
    file_name = datetime.now().strftime("{}_%Y-%m-%d_%I-%M-%S_%p.{}".format(path_prefix, extension))
    return file_name
