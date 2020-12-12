from typing import (
    TypeVar,
    Any,
    Callable,
    List,
    Dict,
)
from decimal import localcontext
from functools import wraps

from typeguard import typechecked

T = TypeVar("T")
S = TypeVar("S")


class IllegalValueException(Exception):
    """Class for encountering illegal arguments."""

    def __init__(
        self,
        message: str,
    ):
        """Initializes an IllegalArgumentException.

        :param message: A message indicating an illegal argument.
        :type message: str
        """
        super().__init__(message)


def expect(
    value_name: str,
    value: T,
    condition_description: str,
    condition: Callable[[T], bool],
) -> None:
    """Throws an exception if value does not meet the condition.

    :param value_name: value name
    :type value_name: str
    :param value: any value
    :type value: T
    :param condition_description: [description]
    :type condition_description: str
    :param condition: [description]
    :type condition: Callable[[T], bool]
    :return: None
    :rtype: None
    """
    message = f"expected {value_name} to {condition_description}"
    if not condition(value):
        raise IllegalValueException(message)


def autorepr(self: Any, attributes: Dict[str, Any]):
    key_eq_val_strs: List[str] = []
    for key, value in attributes.items():
        key_eq_val_strs.append(f"{key}={repr(value)}")
    serial: str = ", ".join(key_eq_val_strs)
    return f"{self.__class__.__name__}({serial})"


@typechecked
def with_precision(precision: int):
    """Makes function run in a copy of the context using specific Decimal precision.

    :param precision: the Decimal precision
    :type precision: int
    :return: wrapped function
    :rtype: Callable
    """

    def decorator(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            with localcontext() as ctx:
                ctx.prec = precision
                return function(*args, **kwargs)

        return wrapped

    return decorator
