""" A tool for capturing console output for logging purposes """

import os
import sys
import threading
import time

from auto_argparser.brain_utils.files import mkdir_p

from io import StringIO


class CaptureOutput:
    """ Capures Standard output while still printing it to console.  e.g.

        with CaptureOutput() as cap:
            print('hello')
            print('goodbye')

        assert cap.read() == 'hello\ngoodbye\n'
    """

    def __init__(self, file_path=None, still_print=True):
        """
        :param file_path: Path to write standard output to, or None to just buffer it in a StrinIO buffer
        :param still_print: Still print to console (in addition to writing to file/buffer)
        """
        if file_path is not None:
            folder, _ = os.path.split(file_path)
            mkdir_p(folder)
        self.file_path = file_path
        self.still_print = still_print
        self._stored_output = None
        self.oldout = None
        self.olderr = None
        self.file_like_object = None

    def __enter__(self):
        self.oldout = sys.stdout
        self.olderr = sys.stderr
        sys.stdout = sys.stderr = self  # type: ignore
        self.file_like_object = StringIO() if self.file_path is None else open(self.file_path, 'w')
        return self

    def write(self, string):
        """ Write to buffer
        :param string: A string
        """
        assert self.file_like_object is not None
        assert self.oldout is not None
        self.file_like_object.write(string)
        if self.still_print:
            self.oldout.write(string)

    def __exit__(self, exc_type, exc_val, exc_tb):
        assert self.oldout is not None
        assert self.olderr is not None
        assert self.file_like_object is not None
        sys.stdout = self.oldout
        sys.stderr = self.olderr
        self.file_like_object.flush()
        if self.file_path is None:
            self._stored_output = self.file_like_object.getvalue()
        self.file_like_object.close()

    def read(self):
        """ Read all captured output since entering this object
        :return str: The captured output up to now
        """
        assert self.file_like_object is not None
        try:
            self.file_like_object.flush()
        except ValueError:
            pass
        if self.file_path is None:
            return self._stored_output if self._stored_output is not None else self.file_like_object.getvalue()
        else:
            with open(self.file_path) as f:
                return f.read()


def capture_value_and_output(func, still_print=True):
    """ Capture output while executing a function

    :param func: Some Callable[[], Any].
    :param still_print: Still print the output.
    :return Tuple[Any, str]: The tuple of (return_value, output_string)
    """
    with CaptureOutput(still_print=still_print) as cap:
        return_val = func()
    return return_val, cap.read()


def capture_output(func, still_print=True):
    """ Capture output while executing a function
    :param func: Some Callable[[], Any].
    :param still_print: Still print the output.
    :return str: The output string
    """
    _, output_string = capture_value_and_output(func, still_print=still_print)
    return output_string


class CaptureCppOutput:
    """
    Capture output from cpp library. Uses dedup2 instead of python streams and therefore is able to capture
    cpp logs from stdout
    https://stackoverflow.com/questions/24277488/in-python-how-to-capture-the-stdout-from-a-c-shared-library-to-a-variable
    """
    def __init__(self):
        self._stdout_fileno = None
        self._stdout_save = None
        self._stdout_pipe = None
        self._capture_thread = None
        self._captured_stdout = None

    def __enter__(self):
        self._stdout_fileno = sys.stdout.fileno()
        self._stdout_save = os.dup(self._stdout_fileno)
        self._stdout_pipe = os.pipe()
        os.dup2(self._stdout_pipe[1], self._stdout_fileno)
        os.close(self._stdout_pipe[1])

        self._captured_stdout = b''

        def drain_pipe():
            assert self._stdout_pipe is not None
            assert self._captured_stdout is not None
            while True:
                data = os.read(self._stdout_pipe[0], 1024)
                if not data:
                    break
                self._captured_stdout += data

        self._capture_thread = threading.Thread(target=drain_pipe)
        self._capture_thread.start()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        assert self._stdout_fileno is not None
        assert self._stdout_save is not None
        assert self._stdout_pipe is not None
        assert self._capture_thread is not None
        assert self._captured_stdout is not None

        # Close the write end of the pipe to unblock the reader thread and trigger it
        # to exit
        os.close(self._stdout_fileno)
        self._capture_thread.join()

        # Clean up the pipe and restore the original stdout
        os.close(self._stdout_pipe[0])
        for _ in range(10):
            try:
                os.dup2(self._stdout_save, self._stdout_fileno)
                break
            except OSError:
                time.sleep(0.1)
        os.close(self._stdout_save)

    def get_captured(self) -> bytes:
        assert self._captured_stdout is not None
        return self._captured_stdout


if __name__ == '__main__':
    with CaptureOutput() as cap:
        print('hello')
        print('goodbye')

    assert cap.read() == 'hello\ngoodbye\n'
