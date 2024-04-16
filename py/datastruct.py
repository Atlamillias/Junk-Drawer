"""A module for creating slotted dataclass-like structures and transforms."""
import types
import inspect
import functools
import itertools
import dataclasses
from dataclasses import field as field
from typing import (
    Any, Callable, Mapping,
    TypeVar, ParamSpec,
    overload, dataclass_transform as dataclass_transform
)


_T = TypeVar("_T")
_P = ParamSpec("_P")

_MISSING = object()



def _cast_object(target: Any, source: _T) -> _T:
    return target


def _slotted_members(cls: type) -> list[str]:
    # This is an expensive procedure, but it cannot be cached. Class
    # dictionaries are mutable, so slots found on a class once may not
    # exist later (unlikely, but possible).
    member_descriptor = types.MemberDescriptorType
    _seen = set()
    return list(itertools.chain(*(
        (
            s for s, v in tp.__dict__.items()
            if isinstance(v, member_descriptor) and s not in _seen and not _seen.add(s)
        )
        for tp in cls.mro()[:-1]
    )))


def _ammend_closure(cls, func):
    """Update the class reference within a method's closure to match that
    of *cls*; correcting the binding of the local `__class__` variable
    and, by extension, fixing zero-argument `super()`.

    *cls* must share a name with the class found on the `__class__`
    attribute local to the function.
    """
    if hasattr(func, '__self__'):
        return func

    if isinstance(func, (classmethod, staticmethod)):
        fn = func.__func__
    elif isinstance(func, property):  # impossible for custom descriptors
        fn = func.fget
    else:
        fn = func

    closure = getattr(fn, '__closure__', None) or ()
    for cell in closure:
        try:
            contents = cell.cell_contents
        except:
            continue
        if isinstance(contents, type) and contents.__name__ == cls.__name__:
            cell.cell_contents = cls


def _update_transform(field_attr: str, field_type: type[Any], transformer: Any, struct_type: Any):

    @functools.wraps(transformer)
    def capture_class(cls=None, /, **kwargs):


        def struct_transform(cls):
            nonlocal kwargs, field_attr, field_type, transformer, struct_type

            class DataStructType(struct_type):
                FIELD_ATTR     = field_attr
                FIELD_TYPE     = field_type
                TRANSFORMER    = transformer
                TRANSFORM_KWDS = tuple(
                    p.name for p in inspect.signature(transformer).parameters.values()
                    if p.kind in (
                        inspect.Parameter.POSITIONAL_OR_KEYWORD,
                        inspect.Parameter.KEYWORD_ONLY,
                    )
                )
                TRANSFORM_DEFAULTS = types.MappingProxyType(kwargs)

                def __new__(mcls, name, bases, namespace, **kwargs):
                    # signal older `StructType` parents to skip processing
                    build_struct = False
                    if '_struct_flag' not in namespace:
                        build_struct = namespace['_struct_flag'] = True

                        new_kwargs  = {}
                        tsfm_kwargs = mcls.TRANSFORM_DEFAULTS.copy()
                        for k, v in kwargs.items():
                            if k in mcls.TRANSFORM_KWDS:
                                tsfm_kwargs[k] = v
                            else:
                                new_kwargs[k] = v

                        tsfm_kwargs.pop('slots', None)
                        tsfm_kwargs.pop('weakref_slot', None)
                        kwargs = new_kwargs

                    cls = super().__new__(mcls, name, bases, namespace, **kwargs)
                    if '_struct_flag' in cls.__dict__:
                        delattr(cls, '_struct_flag')
                    # This check avoids inf recursion if the transformer rebuilds the
                    # class e.g. `dataclass(slots=True`)`.
                    if not build_struct or mcls.FIELD_ATTR in cls.__dict__:
                        return cls

                    # TODO: preserve docstrings when slots is a mapping?
                    cls = mcls.TRANSFORMER(cls, **tsfm_kwargs)  # type: ignore
                    class_slots = tuple(
                        s for s in
                        itertools.chain(
                            cls.__dict__.get(mcls.FIELD_ATTR, ()),
                            ('__weakref__',),
                        )
                        if s not in _slotted_members(cls)[len(class_slots):]  # type: ignore
                    )
                    class_dict = dict(cls.__dict__)
                    class_dict['__slots__'] = class_slots
                    class_dict['_struct_flag'] = True
                    class_dict.pop('__dict__', None)
                    class_dict.pop('__weakref__', None)

                    cls = mcls(name, bases, class_dict, **kwargs)
                    for member in cls.__dict__.values():
                        _ammend_closure(cls, member)

                    return cls


            class_dict = dict(cls.__dict__)
            class_dict.pop('__dict__', None)
            class_dict.pop('__weakref__', None)

            cls = DataStructType(cls.__name__, cls.__bases__, class_dict, **kwargs)

            del class_dict, kwargs, field_attr, field_type, transformer
            return cls  # type: ignore


        kwargs.pop('slots', None)
        kwargs.pop('weakref_slot', None)
        if cls is None:
            return struct_transform
        return struct_transform(cls)


    if struct_type is None:
        struct_type = DataStructType
    return capture_class




class DataStructType(type):
    FIELD_ATTR        : str
    FIELD_TYPE        : str
    TRANSFORMER       : Callable
    TRANSFORM_KWDS    : tuple[str, ...]
    TRANSFORM_DEFAULTS: Mapping[str, Any]


def is_datastruct(o: Any | type[Any]) -> bool:
    """Return True if an object is an instance or subclass of a
    struct or was affected by a datastruct transform."""
    if not isinstance(o, type):
        o = type(o)
    return isinstance(o, DataStructType)


@overload
def datastruct_transformer(field_attr: str, field_type: type[Any], /, transform: Callable[_P, _T], *, struct_type: type[DataStructType] | None = ...) -> Callable[_P, _T]: ...
@overload
def datastruct_transformer(field_attr: str, field_type: type[Any], /, *, struct_type: type[DataStructType] | None = ...) -> Callable[[Callable[_P, _T]], Callable[_P, _T]]: ...
def datastruct_transformer(field_attr: str, field_type: type[Any], /, transform: Any = None, *, struct_type: Any = None):
    """Augment the behavior of an existing dataclass transform.
    Can be used as a decorator.

    Any class passed to the new transform will be updated using the
    original transform. However, the class also becomes a transform
    itself; applying the same transformation to all derived classes.
    Derived classes inherit this behavior.

    Classes updated using the new transform (directly or through
    inheritance) are guaranteed to declare `__slots__` containing its'
    fields and `__weakref__` if member(s) are not already slotted by
    a parenting class.

    Args:
        - field_attr: The name of the attribute that contains a class'
        field names of fields created/added by the original transform
        (e.g. `__dataclass_fields__`).

        - field_type: The field class used by the original transform
        (e.g. `dataclass.Field`).

        - transform: A dataclass transform that will be used to
        update classes. It must accept a class object as the only
        positional-only argument, followed by one or more optional,
        non-positional-only, non-variadic arguments.

        - struct_type: A metaclass derived from `DataStructType`.
        If provided, it will be used as the base class for the
        dedicated metaclass created for the updated transform.


    Keyword arguments passed directly to the augmented transform
    are stored as defaults for transforms made with the affected class.
    Different keywords/values can be used per-class by including them as
    keyword arguments following the base classes used in the class
    definition (eg `class Class(TransformParent, init=False, frozen=True):
    ...`).

    Transform keyword arguments `slots` and `weakref_slot` (if included
    and/or supported by the original transform) will be ignored when
    transforming classes. This is mainly due to the fact that
    `dataclasses.dataclass` (the only dataclass transform in Python's
    standard library) does not allow users to declare `__slots__`
    when passing `slots=True` to the transform (at the time of writing).

    A class that is directly updated using the augmented transform
    is reconstructed using a custom metaclass derived from `DataStructType`.
    Metaclass conflicts should be solved by creating a subclass of
    `DataStructType` and the other conflicting metaclasses, then passing
    the newly derived metaclass via the *struct_type* keyword argument.
    When passing a user-defined `DataStructType` subclass, its' `__new__`
    method (if defined) must call `super().__new__`.

    A base transform class should be decorated with `dataclass_transform`
    to keep type checkers happy.
    """

    def capture_transform(transformer: Callable[_P, _T]) -> Callable[_P, _T]:
        return _update_transform(field_attr, field_type, transformer, struct_type)  # type: ignore

    if transform is None:
        return capture_transform
    return capture_transform(transform)


# Needs to be cast as `dataclasses.dataclass` so type checkers don't
# "forget" it's a transform -- `dataclass_transform` can only be used
# as a decorator.
datastruct = _cast_object(
    datastruct_transformer(
        '__dataclass_fields__',
        dataclasses.Field,
        dataclasses.dataclass
    ),
    dataclasses.dataclass
)
