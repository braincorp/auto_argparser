"""
Deals with creating and destroying temporary files.
"""
import os
import shutil
from contextlib import contextmanager
from tempfile import mkdtemp


@contextmanager
def hold_tempfile(suffix: str = "", delete_after: bool = True):
    """
    Create a temporary file name, whose parent directory exists, and delete once the context closes.  Example usage:

        with hold_tempfile() as fname:
            with open(fname, 'w') as f:
                f.write('aaa')
            with open(fname) as f:
                assert f.read() == 'aaa'

    :param suffix: A suffix to put on the end of the file.  e.g. '.pkl'
    :param delete_after: Delete the file once the context closes.
    """
    with hold_tempdir(delete_after=delete_after) as fdir:
        path = os.path.join(fdir, 'temp_file')
        if suffix:
            path += suffix
        yield path


@contextmanager
def hold_tempdir(path: str = None, delete_after: bool = True, suffix: str = ''):
    """
    Create a temporary directory, and delete once the block closes.  Usage:

        with hold_tempdir() as dir_path:
            ...

    :param path: Optionally, provide the path at which to make the directory
    :param delete_after: Delete the directory once the context closes.
    :param suffix: Directory suffix
    """
    if path is not None:
        full_path = path + suffix
        try:
            os.makedirs(full_path)
        except OSError:
            pass
        tempdir = full_path
    else:
        tempdir = mkdtemp(suffix=suffix)

    try:
        yield tempdir
    finally:
        if delete_after:
            try:
                shutil.rmtree(tempdir)
            except OSError:  # This may happen if the directory was deleted from within the context... in which case it's still ok.
                pass
