from typing import Optional, Iterator


def bracketed_split(string: str, delimiter: str, strip_brackets: bool = False, maxsplit: Optional[int] = None) -> Iterator[str]:
    """ Split a string by the delimiter unless it is inside brackets.
    e.g.
        list(bracketed_split('abc,(def,ghi),jkl', delimiter=',')) == ['abc', '(def,ghi)', 'jkl']
    """
    openers = '[{(<'
    closers = ']})>'
    opener_to_closer = dict(zip(openers, closers))
    opening_bracket = dict()
    current_string = ''
    n_yields = 0
    depth = 0
    for c in string:
        if c in openers:
            depth += 1
            opening_bracket[depth] = c
            if strip_brackets and depth == 1:
                continue
        elif c in closers:
            assert depth > 0, f"You exited more brackets that we have entered in string {string}"
            assert c == opener_to_closer[opening_bracket[depth]], f"Closing bracket {c} did not match opening bracket {opening_bracket[depth]} in string {string}"
            depth -= 1
            if strip_brackets and depth == 0:
                continue
        if depth == 0 and c == delimiter and (maxsplit is None or n_yields < maxsplit):
            yield current_string
            n_yields += 1
            current_string = ''
        else:
            current_string += c
    assert depth == 0, f'You did not close all brackets in string {string}'
    yield current_string


def indent_string(string, indent='  ', include_first=True, include_last=False):
    """
    Indent a string by adding indent after each newline.
    :param string: The string to indent
    :param indent: The string to use as indentation
    :param include_first: Also indent the first line of the string (before the first newline)
    :param include_last: If the string ends on a newline, also add an indent after that.
    :return: A new string.
    """
    base = string.replace('\n', '\n' + indent)
    if include_first:
        base = indent + base
    if not include_last and base.endswith('\n' + indent):
        base = base[:-len(indent)]
    return base
