import os
from auto_argparser.brain_utils.temp_files import hold_tempfile, hold_tempdir


class _TempFileDirTestException(Exception):
    pass


def test_temp_file():

    with hold_tempfile() as fname:
        with open(fname, 'w') as f:
            f.write('aaa')
        with open(fname) as f:
            assert f.read() == 'aaa'

        assert os.path.exists(fname)
    assert not os.path.exists(fname)

    try:
        with hold_tempfile() as fname:
            with open(fname, 'w') as f:
                f.write('bbb')
            with open(fname) as f:
                assert f.read() == 'bbb'
            assert os.path.exists(fname)
            raise _TempFileDirTestException()
    except _TempFileDirTestException:
        pass
    assert not os.path.exists(fname)


def test_hold_tempdir():

    with hold_tempdir() as fdir:
        assert os.path.isdir(fdir)
    assert not os.path.exists(fdir)

    try:
        with hold_tempdir() as fdir:
            assert os.path.isdir(fdir)
            raise _TempFileDirTestException()
    except _TempFileDirTestException:
        pass
    assert not os.path.exists(fdir)


if __name__ == '__main__':
    test_temp_file()
    test_hold_tempdir()
