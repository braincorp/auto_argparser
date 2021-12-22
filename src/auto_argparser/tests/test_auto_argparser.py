from typing import Dict, Sequence, Any, Optional, Union

from attr import attrs
from pytest import raises

from src.auto_argparser import AutoArgParser, AutoArgParserError, AutoArgParsingSwitch, parse_single_arg


def test_help_string():
    """ Just test that we don't get errors on calling help"""

    # TODO: Add ability to inspect docstring for help

    def compute_a_minus_b_v1(a, b):
        return a - b

    def compute_a_minus_b_v2(a: float, b: float) -> float:
        return a - b

    def compute_a_minus_b_v3(a: float, b: float) -> float:
        """ Subtract b from a
        :param a: A number
        :param b: Another number
        :return: The result
        """
        return a - b

    for func in (compute_a_minus_b_v1, compute_a_minus_b_v2, compute_a_minus_b_v3):
        try:
            assert AutoArgParser(func, print_report=False).call_from_command_line('--help')
        except SystemExit as err:
            assert err.code == 0
        else:
            raise Exception('Did not raise system exit when called with help')


def test_auto_arg_parser():
    """
    Test that `AutoArgParser` works as expected.
    """

    def compute_a_minus_b(a: float, b: float) -> float:
        """ Subtract b from a
        :param a: A number
        :param b: Another number
        :return: The result
        """
        return a - b

    assert AutoArgParser(compute_a_minus_b, print_report=False).call_from_command_line('--a=4 --b=5') == -1
    assert AutoArgParser(compute_a_minus_b, print_report=False).call_from_command_line('--b=5 --a=4') == -1
    with raises(AutoArgParserError):
        AutoArgParser(compute_a_minus_b, print_report=False).call_from_command_line('--a=4 --c=5')
    assert AutoArgParser(compute_a_minus_b, print_report=False).call_from_command_line('4 --b=5') == -1
    assert AutoArgParser(compute_a_minus_b, print_report=False).call_from_command_line('4 5') == -1
    assert AutoArgParser(compute_a_minus_b, print_report=False).call_from_command_line('4 5.5') == -1.5
    assert AutoArgParser(compute_a_minus_b, print_report=False).call_from_command_line('5 4') == 1
    assert AutoArgParser(compute_a_minus_b, print_report=False).call_from_command_line('5 -4') == 9
    assert AutoArgParser(compute_a_minus_b, print_report=False).call_from_command_line('5 -4.5') == 9.5

    try:
        assert AutoArgParser(compute_a_minus_b, print_report=False).call_from_command_line('--help')
    except SystemExit as err:
        assert err.code == 0
    else:
        raise Exception('Did not raise system exit when called with help')


def test_boolean_flag_handling():
    def maybe_negate(number: int, negate: bool = False):
        return -number if negate else number

    assert AutoArgParser(maybe_negate).call_from_command_line('--number=3 --negate=true') == -3
    assert AutoArgParser(maybe_negate).call_from_command_line('--number=3 --negate=false') == 3
    assert AutoArgParser(maybe_negate).call_from_command_line('--number=3 --negate=1') == -3
    assert AutoArgParser(maybe_negate).call_from_command_line('--number=3 --negate=0') == 3
    with raises(AutoArgParserError):
        assert AutoArgParser(maybe_negate).call_from_command_line('--number=3 --negate=blahblahblah') == 3
    with raises(AutoArgParserError):
        assert AutoArgParser(maybe_negate).call_from_command_line('--number=3 --negate=2') == 3
    assert AutoArgParser(maybe_negate).call_from_command_line('--number=3 --negate=1') == -3
    assert AutoArgParser(maybe_negate).call_from_command_line('--number=3 --negate') == -3  # Arg alone means True
    assert AutoArgParser(maybe_negate).call_from_command_line('--number=3') == 3


def test_auto_arg_parser_on_method():
    @attrs(auto_attribs=True)
    class Adder:
        base: int

        def add_to(self, other: int):
            return self.base + other

    assert AutoArgParser(Adder(2).add_to).call_from_command_line('--other=3') == 5
    assert AutoArgParser(Adder(2).add_to).call_from_command_line('3') == 5


def test_nested_parsing():
    def identity_dict(arg: Dict[str, int]):
        return arg

    assert AutoArgParser(identity_dict, raise_deep_exceptions=True).call_from_command_line('aaa:3,bbb:4') == dict(aaa=3, bbb=4)

    with raises(AutoArgParserError):
        assert AutoArgParser(identity_dict).call_from_command_line('aaa:3,bbb:ccc') == dict(aaa=3, bbb=4)

    def identity_untyped_dict(arg: Dict[str, Any]):
        return arg

    assert AutoArgParser(identity_untyped_dict).call_from_command_line('aaa:3,bbb:4') == dict(aaa=3, bbb=4)
    assert AutoArgParser(identity_untyped_dict).call_from_command_line('aaa:3,bbb:ccc') == dict(aaa=3, bbb='ccc')

    def identity_seq(arg: Sequence[float]):
        return arg

    assert AutoArgParser(identity_seq).call_from_command_line('3,4,5') == [3., 4., 5.]

    def identity_dictseq(arg: Dict[str, Sequence[int]]):
        return arg

    assert AutoArgParser(identity_dictseq).call_from_command_line('aaa:[3,4,5],bbb:[1,2,3]') == dict(aaa=[3, 4, 5], bbb=[1, 2, 3])

    def identity_dictdict(arg: Dict[str, Dict[str, int]]):
        return arg

    assert AutoArgParser(identity_dictdict).call_from_command_line('aaa:{ddd:3,eee:4},bbb:{fff:5,ggg:6}') == dict(aaa=dict(ddd=3, eee=4), bbb=dict(fff=5, ggg=6))

    # Tricky one where one of the values has a ":" in it
    def identity_dictstr(arg: Dict[str, str]):
        return arg

    assert AutoArgParser(identity_dictstr).call_from_command_line('url:http://www.google.com,name:Google') == dict(url='http://www.google.com', name='Google')
    assert AutoArgParser(identity_dictstr).call_from_command_line('url:[http://www.google.com],name:Google') == dict(url='http://www.google.com', name='Google')
    with raises(AutoArgParserError):
        AutoArgParser(identity_dictstr).call_from_command_line('url:[http://www.news.google.com],name:Google,News')
    assert AutoArgParser(identity_dictstr).call_from_command_line('url:[http://www.news.google.com],name:[Google,News]') == dict(url='http://www.news.google.com',
                                                                                                                                 name='Google,News')


def test_auto_argparsing_switchboard():
    def add(a: float, b: float, print_output=False):
        if print_output:
            print(f'a+b={a + b}')
        return a + b

    def mul(a: float, b: float, print_output=True):
        if print_output:
            print(f'a*b={a + b}')
        return a * b

    board = AutoArgParsingSwitch({'add': add, 'mul': mul})
    assert board.call_from_command_line("add 3 4 --print_output") == 7.
    assert board.call_from_command_line("mul 3 4 --print_output") == 12.
    with raises(AutoArgParserError):
        board.call_from_command_line("div 3 4 --print_output")


def test_call_with_remaining():
    def func_1(a: float, b: float) -> float:
        return a + b

    def func_2(c: float, d: float) -> float:
        return c * d

    ccc, remaining = AutoArgParser(func_1).call_from_command_line_with_remaining("--a=2 --b=3 --d=4")
    eee = AutoArgParser(func_2).call_from_command_line(list(remaining) + [f'--c={ccc}'])
    assert eee == (2 + 3) * 4


def test_parse_single_arg():
    args = '--aaa 5 --bbb 6 --dddd'

    result, remaining = parse_single_arg(args=args, arg_name='bbb')
    assert result == 6
    assert remaining == ['--aaa', '5', '--dddd']

    result, remaining = parse_single_arg(args=remaining, arg_name='aaa')
    assert result == 5
    assert remaining == ['--dddd']

    result, remaining = parse_single_arg(args=args, arg_name='dddd', arg_type=bool)
    assert result is True
    assert remaining == ['--aaa', '5', '--bbb', '6']

    with raises(AutoArgParserError):  # Because without bool specification you don't know its a flag
        parse_single_arg(args=args, arg_name='dddd')

    result, remaining = parse_single_arg(args='--aaa 5 --bbb 6 --dddd False', arg_name='dddd')  # Should guess from value
    assert result is False
    assert remaining == ['--aaa', '5', '--bbb', '6']

    result, remaining = parse_single_arg(args=args, arg_name='bbb', arg_type=str)
    assert result == '6'
    assert remaining == ['--aaa', '5', '--dddd']

    with raises(AutoArgParserError):
        parse_single_arg(args='--aaa 5 --bbb abc --dddd', arg_name='bbb', arg_type=int)

    with raises(AutoArgParserError):
        parse_single_arg(args=args, arg_name='eee')

    result, remaining = parse_single_arg(args=args, arg_name='eee', default=7.)
    assert result == 7.
    assert remaining == ['--aaa', '5', '--bbb', '6', '--dddd']


def test_construct_attr_object():
    @attrs(auto_attribs=True)
    class Person:
        name: str
        age: int

    result = AutoArgParser(Person).call_from_command_line('--name Suzy --age 30')
    assert result == Person(name='Suzy', age=30)


def test_nested_attrs_call():
    @attrs(auto_attribs=True)
    class Person:
        name: str
        age: int

    def greet_persion(greeting: str, person: Person):
        result = f"{greeting} {person.name}, how was your {person.age}'th birthday?"
        return result

    aap = AutoArgParser(greet_persion)
    result = aap.call_from_command_line('--greeting Hello --person.name Suzy --person.age 30')
    assert result == "Hello Suzy, how was your 30'th birthday?"


def test_parse_optional_arg():
    def func1(a: Optional[int]) -> Optional[int]:
        return a

    result, _ = AutoArgParser(func1).call_from_command_line_with_remaining("--a=None")
    assert result is None

    result, _ = AutoArgParser(func1).call_from_command_line_with_remaining("--a=54")
    assert result == 54 and isinstance(result, int)

    def func2(a: Union[int, float, Sequence[int]]) -> Union[int, float, Sequence[int]]:
        return a

    result, _ = AutoArgParser(func2).call_from_command_line_with_remaining("--a=54")
    assert result == 54 and isinstance(result, int)

    result, _ = AutoArgParser(func2).call_from_command_line_with_remaining("--a=3.14")
    assert result == 3.14 and isinstance(result, float)

    result, _ = AutoArgParser(func2).call_from_command_line_with_remaining("--a=54,32,23")
    assert result[0] == 54 and result[-1] == 23 and isinstance(result, list)

    with raises(AutoArgParserError):
        AutoArgParser(func2).call_from_command_line_with_remaining("--a=3.14,32,23")

    def func3(a: Any) -> Any:
        return a

    result, _ = AutoArgParser(func3).call_from_command_line_with_remaining("--a=None")
    assert result is None

    result, _ = AutoArgParser(func3).call_from_command_line_with_remaining("--a=54")
    assert result == 54 and isinstance(result, int)


if __name__ == '__main__':
    test_help_string()
    test_auto_arg_parser()
    test_boolean_flag_handling()
    test_auto_arg_parser_on_method()
    test_nested_parsing()
    test_auto_argparsing_switchboard()
    test_call_with_remaining()
    test_parse_single_arg()
    test_construct_attr_object()
    test_nested_attrs_call()
    test_parse_optional_arg()
