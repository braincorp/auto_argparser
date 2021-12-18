from pytest import raises

from auto_argparser.brain_utils.string_utils import bracketed_split


def test_bracketed_split():

    assert list(bracketed_split('abc,def,ghi', delimiter=',')) == ['abc', 'def', 'ghi']
    assert list(bracketed_split('abc,(def,ghi),jkl', delimiter=',')) == ['abc', '(def,ghi)', 'jkl']
    assert list(bracketed_split('abc,(def,ghi),jkl', delimiter=',', strip_brackets=True)) == ['abc', 'def,ghi', 'jkl']
    assert list(bracketed_split('abc,(def,(ghi,jkl))', delimiter=',', strip_brackets=True)) == ['abc', 'def,(ghi,jkl)']
    assert list(bracketed_split('abc,(def,((ghi,jkl), mno))', delimiter=',', strip_brackets=True)) == ['abc', 'def,((ghi,jkl), mno)']
    assert list(bracketed_split('abc,(def,((ghi,jkl), mno))', delimiter=',', strip_brackets=False)) == ['abc', '(def,((ghi,jkl), mno))']
    assert list(bracketed_split('abc,(def,[(ghi,jkl), mno])', delimiter=',', strip_brackets=False)) == ['abc', '(def,[(ghi,jkl), mno])']
    assert list(bracketed_split('abc,def,ghi', delimiter=',', maxsplit=1)) == ['abc', 'def,ghi']
    assert list(bracketed_split('abc,[def,ghi],jkl', delimiter=',', maxsplit=1)) == ['abc', '[def,ghi],jkl']

    with raises(AssertionError):
        list(bracketed_split('abc,(def,ghi]', delimiter=','))
    with raises(AssertionError):
        list(bracketed_split('abc,(def,ghi', delimiter=','))
    with raises(AssertionError):
        list(bracketed_split('abc,(def,ghi))', delimiter=','))

    assert list(bracketed_split('', delimiter=',')) == ['']
    assert list(bracketed_split('abc', delimiter=',')) == ['abc']
