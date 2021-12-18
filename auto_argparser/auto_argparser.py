import inspect
import re
import shlex
import sys
import time
from argparse import ArgumentParser, ArgumentTypeError, RawTextHelpFormatter
from collections import namedtuple, OrderedDict
from datetime import datetime
from enum import IntEnum
from typing import Sequence, Dict, Optional, Callable, Any, List, Tuple, Set, Union, Mapping

import attr
from attr import attrs
from more_itertools import zip_equal  # type: ignore

from auto_argparser.brain_utils.capture_output import CaptureOutput
from auto_argparser.brain_utils.type_utils import get_origin, get_args, is_optional_type, get_optional_type
from auto_argparser.brain_utils.string_utils import bracketed_split, indent_string

ArgSpec = namedtuple('ArgSpec', ['name', 'type', 'default', 'doc'])


class NoValue:
    """ Placeholder for no value being provided """


def parse_docstring(docstring: str) -> Dict[str, str]:
    """ Parse a docstring into a dict mapping argument name to docstring """
    argument_pattern = re.compile(r" *:param ([a-zA-Z0-9_]*)( *)(.*?):( *)(.*)")
    return {match.group(1): match.group(5) for line in docstring.split('\n') for match in [argument_pattern.match(line)] if match is not None}


def get_maybe_optional_type(type_annotation):
    """ Get the underlying type of an annotation if it is optional - or just return type if it is not.  E.g.
        get_maybe_optional_type(Optional[float]) is float
        get_maybe_optional_type(float) is float
    :param type_annotation: A type annotation which may be optional
    :return: The inner type
    """
    return get_optional_type(type_annotation) if is_optional_type(type_annotation) else type_annotation


def parse_argstring_with_type(argstring: str, seq_type) -> Any:
    """ Parse an argstring representing a sequence, e.g.
        parse_sequence_argstring('afds,cds', Sequence[str]) == ['afds', 'cds']
        parse_sequence_argstring('2,3', Sequence[int]) == [2, 3
    :param argstring: A command line argument value representing a comma-separated sequence
    :param seq_type: The type annotation
    :return: The parsed object
    """
    converter = get_appropriate_type_converter(seq_type)
    return converter(argstring)


def _add_arg_to_parser(parser: ArgumentParser, arg_strings: Sequence[str], arg_name: str, arg_type: Any = NoValue, arg_doc=NoValue, default=NoValue,
                       type_converter: Optional[Callable[[str], Any]] = None, short_name: Optional[str] = None):
    """ Add an argument to the parser object """
    args = ('-' + short_name,) if short_name is not None else ()
    args += ('--' + arg_name,)
    arg_type_guess = arg_type if arg_type is not NoValue else type(default) if default is not NoValue else None

    is_flag = False
    if arg_type_guess == bool:  # Allow for "boolean flags" that do not need to be followed by a value because they just mark true
        for i, argstr in enumerate(arg_strings):
            if '=' not in argstr and argstr.lstrip('-') == arg_name or short_name is not None and argstr.lstrip('-') == short_name:
                if i == len(arg_strings) - 1 or arg_strings[i + 1].startswith('-'):  # Means that value is not specified
                    is_flag = True
                    break

    type_conv = type_converter if type_converter is not None else get_appropriate_type_converter(arg_type_guess) if arg_type_guess is not None else parse_string_guessing_type
    parser.add_argument(*args,
                        help=None if arg_doc is NoValue else arg_doc,
                        default=default,
                        **(dict(action='store_true') if is_flag else dict(type=type_conv)))  # type: ignore


def parse_single_arg(args: Union[str, Sequence[str]], arg_name: str, arg_type=NoValue, default: Any = NoValue, factory: Optional[Callable[[], Any]] = None,
                     short_name: Optional[str] = None) -> Tuple[Any, Sequence[str]]:
    """ Parse an arg out of the sequence, returning its value and the remaining args.
    :param args: The arg string or separated list of arg strings.  E.g. '--aaa 5 --bbb 6 --dddd' or ['--aaa', '5', '--bbb', '6', '--dddd']
    :param arg_name: The name of the arg, e.g. bbb
    :param arg_type: The type of the arg
    :param default: The default value if the arg is not given in the string
    :param short_name: Optional short name for the arg, e.g. 'b'
    :return: The value of the parsed arg, and the list of remaining args.
    """
    if isinstance(args, str):
        args = shlex.split(args)
    parser = ArgumentParser()
    _add_arg_to_parser(parser=parser, arg_strings=args, arg_name=arg_name, arg_type=arg_type, short_name=short_name, default=default)
    try:
        with CaptureOutput() as cap:
            names, remaining = parser.parse_known_args(args)
    except SystemExit:
        error_text = cap.read()
        raise AutoArgParserError(f'Error whan parsing arg {arg_name} from "{" ".join(args)}": {error_text}')
    arg_value = getattr(names, arg_name)
    if arg_value is NoValue:
        if factory is not None:
            arg_value = factory()
        else:
            raise AutoArgParserError(f'Could not get a value for arg {arg_name} from "{" ".join(args)}"')
    return arg_value, remaining


def str2bool(bool_argstring: str) -> bool:
    """
    Convert a human-readable string command line argument to a boolean value.
    :param bool_argstring: The string which indicates a boolean
    :return bool: The boolean
    """
    # From https://stackoverflow.com/a/43357954/851699
    if bool_argstring.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif bool_argstring.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise ArgumentTypeError(f'Boolean value expected, but got "{bool_argstring}".')


def get_appropriate_type_converter(type_annotation) -> Callable[[str], 'type_annotation']:  # type: ignore
    """ Get the appropriate converter for the string annotatoin
    :param type_annotation: A type annotation
    :return: The converter which maps a command-line arg to the appropriate type
    """
    origin_type = get_origin(type_annotation)
    if origin_type in (Mapping, Dict):
        def convert_mapping_string(string_rep):
            """ Convert a string like aaa=3,bbb=4 into a dict {'aaa': 3, 'bbb': 2} """
            key_type, value_type = get_args(type_annotation)
            key_converter = get_appropriate_type_converter(key_type)
            val_converter = get_appropriate_type_converter(value_type)
            kv_pairs = [tuple(bracketed_split(substr, ':', strip_brackets=True, maxsplit=1)) for substr in bracketed_split(string_rep, delimiter=',', strip_brackets=False)]

            if not all(len(p) == 2 for p in kv_pairs):
                raise AutoArgParserError(f'We expect a string containing colon-separated pairs like "key1:val1,key2:val2".  \n... '
                                         f'Got "{string_rep}", which splits into {kv_pairs}')
            return OrderedDict((key_converter(k), val_converter(v)) for k, v in kv_pairs)

        return convert_mapping_string
    elif origin_type in (Sequence, List, Set):
        def convert_sequence_string(string_rep):
            constructor = {Sequence: list, List: list, Set: set}[origin_type]
            subtype, = get_args(type_annotation)
            return constructor(get_appropriate_type_converter(subtype)(s) for s in bracketed_split(string_rep, delimiter=',', strip_brackets=True))

        return convert_sequence_string
    elif origin_type is Tuple:
        def convert_sequence_string(string_rep):
            subtypes = get_args(type_annotation)
            string_reps = string_rep.split(',')
            assert len(subtypes) == len(string_reps), f"The length of type args for this tuple: {subtypes} ({len(subtypes)}) does not match the " \
                                                      f"length of provided values: {string_reps} ({len(string_reps)})"
            return tuple(get_appropriate_type_converter(subtype)(s) for subtype, s in zip(subtypes, string_reps))

        return convert_sequence_string
    elif origin_type is Union:
        def convert_union_string(string_rep):
            subtypes = get_args(type_annotation)
            if string_rep == 'None' and type(None) in subtypes:  # pylint:disable=unidiomatic-typecheck
                return None
            else:
                for subtype in subtypes:
                    try:
                        return get_appropriate_type_converter(subtype)(string_rep)
                    except:
                        continue
                raise AutoArgParserError(f"Provided value {string_rep} doesn't seem to match any of the union types: {subtypes}")

        return convert_union_string

    elif type_annotation is datetime:
        import dateparser  # type: ignore
        # Import done in here to minimize complaining during transisition
        return dateparser.parse
    elif type_annotation is bool:
        return str2bool
    elif type_annotation in (int, float, str):
        return type_annotation
    elif inspect.isclass(type_annotation) and issubclass(type_annotation, IntEnum):
        return int
    elif type_annotation is Any:
        return parse_string_guessing_type
    else:
        return str


def parse_string_guessing_type(string):
    """ Parse a string while guessing the appropriate type based on the form of the strign.
    :param string: Any string specifying a value
    :return:The value
    """
    string = string.strip(' ')
    if string.isnumeric():
        return int(string)
    elif all(s in '1234567890.' for s in string.lstrip('-')):
        return float(string)
    elif string.lower() == 'none':
        return None
    elif string.lower() in ('true', 'false'):
        return str2bool(string)
    elif string.startswith("'") or string.startswith('"'):
        return string.strip('"\'')
    else:
        return string


def separate_subargs_under_name(args: Sequence[str], name: str, short_name: Optional[str] = None) -> Tuple[Sequence[str], Sequence[str]]:
    """
    Separate out args with the given under the given name.  E.g.
        separate_args_with_prefix(['--greeting',  'hello', '--person.name', 'Suzy', '--person.age', '30'], prefix='person')
            == ['--name', 'Suzy', '--age', '30'], ['--greeting',  'hello']
    :param args:
    :param name: The arg
    :param short_name: Optionall, the shortened prefix, e.g. 'p'
    :return:
    """
    keepers = []
    remainders = []
    last_was_keeper = False
    for argstr in args:
        is_argument_key = argstr.startswith('-') and len(argstr.lstrip('-.,0123456789')) != 0
        if is_argument_key:
            full_prefix = f'--{name}.'
            short_prefix = f'-{short_name}.' if short_name is not None else None
            if argstr.startswith(full_prefix):
                subarg = argstr[len(full_prefix):]
                keepers.append('--' + subarg)
                last_was_keeper = True
            elif short_prefix is not None and argstr.startswith(short_prefix):
                subarg = argstr[len(short_prefix):]
                keepers.append('--' + subarg)
                last_was_keeper = True
            else:
                remainders.append(argstr)
                last_was_keeper = False
        elif last_was_keeper:
            keepers.append(argstr)
            last_was_keeper = False
        else:
            remainders.append(argstr)

    return keepers, remainders


class AutoArgParserError(Exception):
    """ An error when the arguments can not be parsed"""


class ArgHelpException(Exception):
    """ Raised on a --help call to terminate the process"""


class AutoArgParser:
    """ Easy tool for making a functon command-line callable.

    def print_a_plus_b(a: float, b: float = 3.):
        print(f"{a}+{b}={a + b}")


    AutoArgParser(print_a_plus_b).call_from_command_line('--a=4 --b=5')
    or
    AutoArgParser(print_a_plus_b).call_from_command_line('4 5')
    """

    def __init__(self, function, arg_converters: Optional[Dict[str, Callable[[str], Any]]] = None, default_overrides: Optional[Mapping[str, Any]] = None,
                 short_names: Optional[Dict[str, str]] = None, return_converter: Callable[[Any], str] = str, print_report=False, raise_deep_exceptions=False):
        """
        :param function: A function which you would like to make command-line callable
        :param arg_converters: A dict mapping arg name to arg converter.  These optionally convert string args into objects
        :param short_names: Optionally, a dict mapping arg names to short names, eg. {'assist_id': 'a'} , so you could go '-a=4BEDBSVZ1DNMZGA4E4BK1YAQHQ'
        """
        self.function = function
        self._short_names = {} if short_names is None else short_names
        self._arg_converters = {} if arg_converters is None else arg_converters
        self._return_converter = return_converter
        self._print_report = print_report
        self._raise_deep_exceptions = raise_deep_exceptions
        spec = inspect.getfullargspec(function)
        if spec.varkw is None:  # If there are no **kwargs, validate that all "short names" and "arg converter" keys are actual named arguments
            if short_names is not None:
                assert set(short_names).issubset(spec.args), f"Short names {set(short_names).difference(spec.args)} do " \
                                                             f"not exist in the list of args to function {function.__name__}"
            if arg_converters is not None:
                assert set(arg_converters).issubset(spec.args), f"Arg converters names {set(arg_converters).difference(spec.args)} do " \
                                                                f"not exist in the list of args to function {function.__name__}"

        arg_docs = parse_docstring(function.__doc__) if function.__doc__ is not None else {}

        defaults = [NoValue] * len(spec.args) if spec.defaults is None else [NoValue] * (len(spec.args) - len(spec.defaults)) + list(spec.defaults)
        argspecs = [
            ArgSpec(name=name,
                    type=spec.annotations[name] if name in spec.annotations else NoValue,
                    default=default if default_overrides is None or name not in default_overrides else default_overrides[name],
                    doc=arg_docs[name] if name in arg_docs else NoValue
                    ) for name, default in zip_equal(spec.args, defaults)]
        self._args = argspecs[1:] if inspect.ismethod(function) or inspect.isclass(self.function) else argspecs

    @classmethod
    def decorator(cls, arg_converters: Optional[Dict[str, Callable[[str], Any]]] = None, short_names: Optional[Dict[str, str]] = None) -> Callable[[Callable], 'AutoArgParser']:
        """ Use this to parameterize the AutoArgParser und use as a decorator.  E.g.

            @AutoArgParser.decorator(short_names=dict(telemetry_id='k'))
            def replay_bag(telemetry_id):
                ...
        """

        def wrapper(func):
            parser = AutoArgParser(func, arg_converters=arg_converters, short_names=short_names)
            func.call_from_command_line = parser.call_from_command_line
            return func

        return wrapper

    def __call__(self, *args, **kwargs):
        """ Just a wrapper.
        :param args: The args
        :param kwargs: The kwargs
        :return: The return value of function
        """
        return self.function(*args, **kwargs)

    def parse_arg_string_and_remaining(self, arg_strings: Union[str, Sequence[str]], allow_remaining: bool = False
                                       ) -> Tuple[Dict[str, Any], Sequence[str]]:
        """ Parse the command line args into a keyward arg dict"""

        if isinstance(arg_strings, str):
            arg_strings = shlex.split(arg_strings)
        arg_strings = list(arg_strings)

        # Enable pass-by-order by inserting names
        for i, (argstr, arg_name) in enumerate(zip(arg_strings, (argspec.name for argspec in self._args))):
            is_argument_key = argstr.startswith('-') and len(argstr.lstrip('-.,0123456789')) != 0
            if is_argument_key:  # Once we start passing by name, it's off
                break
            else:
                arg_strings[i] = f'--{arg_name}={argstr}'

        # Go through args in signature and define types
        parser = ArgumentParser(add_help=True, description=self.function.__doc__, formatter_class=RawTextHelpFormatter)
        sub_kwargs = {}
        direct_arg_strings: Sequence[str] = arg_strings
        for argspec in self._args:
            if attr.has(argspec.type):
                sub_argstrings, direct_arg_strings = separate_subargs_under_name(args=direct_arg_strings, name=argspec.name, short_name=self._short_names.get(argspec.name, None))
                sub_kwargs[argspec.name] = AutoArgParser(argspec.type).call_from_command_line(sub_argstrings)
            else:
                _add_arg_to_parser(
                    parser=parser,
                    arg_strings=arg_strings,
                    arg_name=argspec.name,
                    arg_type=argspec.type,
                    arg_doc=argspec.doc,
                    default=argspec.default,
                    type_converter=self._arg_converters[argspec.name] if argspec.name in self._arg_converters else None,
                    short_name=self._short_names[argspec.name] if argspec.name in self._short_names else None
                )

        # The following trickiness is necessary because of the weird way ArgParser handles exceptions
        error_occurred = False

        remaining: List[str] = []
        try:
            with CaptureOutput() as cap:
                if allow_remaining:
                    args, remaining = parser.parse_known_args(direct_arg_strings)  # type: ignore
                else:
                    args = parser.parse_args(direct_arg_strings)  # type: ignore
        except SystemExit as err:
            if err.code == 0:  # Happens when called with -h --help.
                raise  # TODO: Maybe in future capure output and raise exception with output text.  For now this works
            error_occurred = True
            if self._raise_deep_exceptions:
                raise AutoArgParserError(err)
        if error_occurred:
            error_text = indent_string(cap.read(), '.   ').rstrip('\n')
            raise AutoArgParserError(f'Error when feeding args "{" ".join(arg_strings)}" to {self.function.__name__}(...):\n{error_text}\n'
                                     f'.   You can set raise_deep_exceptions=True to help identify the source.')
        kwargs = {k: v for k, v in vars(args).items() if v is not NoValue}
        kwargs.update(sub_kwargs)

        if not allow_remaining and len(remaining) > 0:
            print(f'Arguments {remaining} were not consumed by {self.function} and allow_remaining is not True')

        return kwargs, remaining

    def call_from_command_line_with_remaining(self, arg_strings: Union[str, Sequence[str]] = tuple(sys.argv[1:]), allow_remaining: bool = True) -> Tuple[Any, Sequence[str]]:
        """ Call the wrapped function from command line args
        :param arg_strings: The command line argument strings, e.g. "--n_threads 7 --bool_var=1 --indices=4,2,5
        :return: (Whatever the function returns, remaining args not consumed)
        """
        kwargs, remaining = self.parse_arg_string_and_remaining(arg_strings, allow_remaining=allow_remaining)
        tstart = time.time()
        return_val = self.function(**kwargs)
        elapsed = time.time() - tstart
        if self._print_report:
            report = f"........\nCall to '{self.function.__name__} {' '.join(arg_strings) if not isinstance(arg_strings, str) else arg_strings}' took {elapsed:.2f}s"
            if return_val is not None:
                return_str = self._return_converter(return_val)
                if '\n' in return_str or len(return_str) > 80:
                    return_str = '\n-----\n' + return_str.strip('\n')
                report += ' and returned ' + return_str
            print(report)
        return return_val, remaining

    def call_from_command_line(self, arg_strings: Union[str, Sequence[str]] = tuple(sys.argv[1:])) -> Any:
        """ Call the wrapped function from command line args
        :param arg_strings: The command line argument strings, e.g. "--n_threads 7 --bool_var=1 --indices=4,2,5
        :return: Whatever the function returns
        """
        return_val, _ = self.call_from_command_line_with_remaining(arg_strings=arg_strings, allow_remaining=False)
        return return_val


@attrs(auto_attribs=True)
class AutoArgParsingSwitch:
    """ A "Switch" which lets you chose a function with the first arg and pass the remaining args to that function:

        def add(a:float, b:float, print_output = False):
            if print_output:
                print(f'a+b={a+b}')
            return a+b

        def mul(a:float, b:float, print_output = True):
            if print_output:
                print(f'a*b={a+b}')
            return a*b

        switch = AutoArgParsingSwitch({'add': add, 'mul': mul})
        switch.call_from_command_line("add 3 4 --print_output")
    """

    named_funcs: Dict[str, Union[AutoArgParser, Callable]]

    def call_from_command_line(self, arg_strings: Union[str, Sequence[str]] = tuple(sys.argv[1:])) -> Any:
        """ Select a function and call it from command line,
        :param arg_strings: The command line argument strings, e.g. "add 3 4 --save_output"
        :return: Whatever the function returns
        """
        if isinstance(arg_strings, str):
            arg_strings = shlex.split(arg_strings)
        if len(arg_strings) == 0:
            raise AutoArgParserError(f"You didn't specify a function to call.  Options: {list(self.named_funcs)}")
        func_str = arg_strings[0]
        if func_str not in self.named_funcs:
            raise AutoArgParserError(f"No function {func_str} in options: {list(self.named_funcs)}")
        func = self.named_funcs[func_str]
        if not isinstance(func, AutoArgParser):
            func = AutoArgParser(func)
        return func.call_from_command_line(arg_strings=arg_strings[1:])


def print_a_plus_b(a: float, b: float = 3.):
    """ Example function
    :param a: Something
    :param b: Somethings else
    """
    print(f"{a}+{b}={a + b}")


if __name__ == '__main__':
    AutoArgParser(print_a_plus_b).call_from_command_line(['--a=4'])
