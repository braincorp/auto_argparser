from open.brain_utils.capture_output import CaptureOutput, CaptureCppOutput
from open.brain_utils.temp_files import hold_tempfile


def test_capture_output():

    # Mode 1: To file
    with hold_tempfile() as fpath:
        with CaptureOutput(file_path=fpath) as cap:
            print('hello')
            print('goodbye')
            assert cap.read() == 'hello\ngoodbye\n'
        assert cap.read() == 'hello\ngoodbye\n'
        with open(fpath) as f:
            assert f.read() == 'hello\ngoodbye\n'

    # Mode 2: To memory
    with CaptureOutput() as cap:
        print('hello')
        print('goodbye')

        assert cap.read() == 'hello\ngoodbye\n'
    assert cap.read() == 'hello\ngoodbye\n'


def test_cpp_capture_out():
    with CaptureCppOutput() as cap:
        # TODO: ideally, should be tested with cpp library
        print('hello')
        print('goodbye')

    assert cap.get_captured().decode() == 'hello\ngoodbye\n'


if __name__ == '__main__':
    test_capture_output()
    test_cpp_capture_out()
