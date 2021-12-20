from typing import Union


def get_origin(type_annotation):
    """ Backport of python 3.8's get_origin.  e.g. get_origin(Tuple[str, int]) is Tuple
    :param type_annotation: A type annotation, e.g Tuple[str, int]
    :return: The base type, e.g. Tuple
    """
    is_generic_annotation = hasattr(type_annotation, '__origin__') and type_annotation.__origin__ is not None
    return type_annotation.__origin__ if is_generic_annotation else type_annotation


def get_args(type_annotation):
    """ Backport of python 3.8's get_args.  E.g. get_args(Tuple[str, int]) == (str, int)
    :param type_annotation: A type annotation, e.g. Tuple[str, int]
    :return: The arguments to that annotation, e.g. (str, int)
    """
    return type_annotation.__args__


def is_optional_type(type_annotation) -> bool:
    """ Determines if a type is Optional[XXX]
    :param type_annotation: A type annotation, e.g Optional[float] or float
    :return: Whether the type annotation is an optional
    """
    if get_origin(type_annotation) is Union:
        args = get_args(type_annotation)
        return len(args) == 2 and type(None) in args  # pylint:disable=unidiomatic-typecheck
    return False


def get_optional_type(type_annotation):
    """ Get the type behind an optional.  E.g. get_optional_type(Optional[float]) == float
    :param type_annotation: A type annotation, e.g. Optional[float]
    :return: The base type, e.g. float
    """
    assert is_optional_type(type_annotation)
    base_type, _ = get_args(type_annotation)
    return base_type
