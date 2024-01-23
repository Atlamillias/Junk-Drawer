from typing import overload, Any, Mapping, Iterable, Callable, Sequence, MutableSequence, TypeVar, Self
import sys
import enum
import types
import threading
import abstract



T     = TypeVar("T")
_T_co = TypeVar("_T_co", covariant=True)




# [Dynamic Code Generation]

def create_module(
    name : str,
    body : Mapping[str, Any] | Iterable[tuple[str, Any]] = (),
    attrs: Mapping[str, Any] | Iterable[tuple[str, Any]] = (),
) -> types.ModuleType:
    """Create a new module object.

    Args:
        - name: Name for the new module.

        - body: Used to update the module's contents/dictionary.

        - attrs: Used to update the module's attributes.
    """
    m = types.ModuleType(name, None)
    for k, v in tuple(attrs):
        setattr(m, k, v)
    m.__dict__.update(body)

    return m


@overload
def create_function(name: str, args: Sequence[str], body: Sequence[str], return_type: T = Any, module: str = '', *, globals: dict[str,  Any] | None = None, locals: Mapping[str,  Any] | Iterable[tuple[str,  Any]] = ()) -> Callable[..., T]: ...  # type: ignore
def create_function(name: str, args: Sequence[str], body: Sequence[str], return_type: T = Any, module: str = '', *, globals: dict[str,  Any] | None = None, locals: Mapping[str,  Any] | Iterable[tuple[str,  Any]] = (), __default_module=create_module('')) -> Callable[..., T]:
    """Compile a new function from source.

    Args:
        * name: Name for the new function.

        * args: A sequence containing argument signatures (as strings)
        for the new function. Each value in *args* should be limited to
        a single argument signature.

        * body: A sequence containing the source that will be executed when
        the when the new function is called. Each value in the sequence should
        be limited to one line of code.

        * return_type: Object to use as the function's return annotation.

        * module: Used to update the function's `__module__` attribute
        and to fetch the appropriate global mapping when *globals* is
        None.

        * globals: The global scope for the new function.

        * locals: The (non)local scope for the new function.


    When *globals* is None, this function will attempt to look up *module*
    in `sys.modules`, and will use the returned module's dictionary as
    *globals* if found. If the module could not be found or both *module*
    and *globals* are unspecified, *globals* defaults to the dictionary of
    a dedicated internal dummy module.

    Note that, when including *locals*, the created function's local scope
    will not be *locals*, but a new mapping created from its' contents.
    However, *globals* is used as-is.

    """
    assert not isinstance(body, str)
    body = '\n'.join(f'        {line}' for line in body)

    locals = dict(locals)
    locals["_return_type"] = return_type

    if globals is None:
        if module in sys.modules:
            globals = sys.modules[module].__dict__
        else:
            globals = __default_module.__dict__

    closure = (
        f"def __create_function__({', '.join(locals)}):\n"
        f"    def {name}({', '.join(args)}) -> _return_type:\n{body}\n"
        f"    return {name}"
    )

    scope = {}
    exec(closure, globals, scope)

    fn = scope["__create_function__"](**locals)
    fn.__module__   = module or __default_module.__name__
    fn.__qualname__ = fn.__name__ = name

    return fn




# [Inspection Tools]

class PyTypeFlag(enum.IntFlag):
    """Python type bit masks (`type.__flags__`, `PyTypeObject.tp_flags`).

    A type's flag bit mask is created when the object is defined --
    changing it from Python does nothing helpful.
    """
    STATIC_BUILTIN           = (1 << 1)  # (undocumented, internal)
    MANAGED_WEAKREF          = (1 << 3)
    MANAGED_DICT             = (1 << 4)
    PREHEADER                = (MANAGED_WEAKREF | MANAGED_DICT)
    SEQUENCE                 = (1 << 5)
    MAPPING                  = (1 << 6)
    DISALLOW_INSTANTIATION   = (1 << 7)  # `tp_new == NULL`
    IMMUTABLETYPE            = (1 << 8)
    HEAPTYPE                 = (1 << 9)
    BASETYPE                 = (1 << 10)  # allows subclassing
    HAVE_VECTORCALL          = (1 << 11)
    READY                    = (1 << 12)  # fully constructed type
    READYING                 = (1 << 13)  # type is under construction
    HAVE_GC                  = (1 << 14)  # allow garbage collection
    HAVE_STACKLESS_EXTENSION = (3 << 15)  # Stackless Python
    METHOD_DESCRIPTOR        = (1 << 17)  # behaves like unbound methods
    VALID_VERSION_TAG        = (1 << 19)  # has up-to-date type attribute cache
    ABSTRACT                 = (1 << 20)  # `ABCMeta.__new__`
    MATCH_SELF               = (1 << 22)  # "builtin" class pattern-matting behavior (undocumented, internal)
    ITEMS_AT_END             = (1 << 23)  # items at tail end of instance memory
    LONG_SUBCLASS            = (1 << 24)  # |- used for `Py<type>_Check`, `isinstance`, `issubclass`
    LIST_SUBCLASS            = (1 << 25)  # |
    TUPLE_SUBCLASS           = (1 << 26)  # |
    BYTES_SUBCLASS           = (1 << 27)  # |
    UNICODE_SUBCLASS         = (1 << 28)  # |
    DICT_SUBCLASS            = (1 << 29)  # |
    BASE_EXC_SUBCLASS        = (1 << 30)  # |
    TYPE_SUBCLASS            = (1 << 31)  # |


def has_feature(cls: type[Any], flag: int | PyTypeFlag):
    """Python implementation of CPython's `PyType_HasFeature` macro."""
    return bool(cls.__flags__ & flag)


def managed_dict_type(o: Any) -> bool:
    """Check if an instance, or future instances of a class, support
    the dynamic assignment of new members/variables.

    Args:
        - o: Class or instance object to inspect.


    If *o* is an instance object, this function returns True if it has
    a `__dict__` attribute. For class objects; return True if instances
    of that class are expected to have a `__dict__` attribute, instead.

    This function will return False on "slotted" classes if any of its'
    non-builtin bases did not declare `__slots__` at the time of their
    creation.
    """
    if not isinstance(o, type):
        o = type(o)
    return has_feature(o, PyTypeFlag.MANAGED_DICT)


def is_cclass(o: Any):
    """Return True if an object is a class implemented in C."""
    return isinstance(o, type) and not has_feature(o, PyTypeFlag.HEAPTYPE)


def is_cfunction(o: Any) -> bool:
    """Return True if an object is a function implemented in C. This
    includes built-in functions like `len` and `isinstance`, as well
    as those exported in C-extensions.
    """
    return isinstance(o, types.BuiltinFunctionType)


@overload
def is_builtin(o: Any) -> bool: ...  # type: ignore
def is_builtin(o: Any, *, __module=type.__module__) -> bool:
    """Return True if an object is a built-in function or class.

    Unlike `inspect.isbuiltin`, the result of this function is not
    falsified by C-extension objects, and can also identify built-in
    classes.

    Args:
        - o: Object to test.
    """
    try:
        return o.__module__ == __module
    except:
        return False


@overload
def is_mapping(o: Any) -> bool: ...  # type: ignore
def is_mapping(o: Any, *, __key=object()):
    """Return True if an object implements the basic behavior of a
    mapping.

    Useful to validate an object based on protocol rather than type;
    objects need not be derived from `Mapping` to be considered a
    mapping or mapping-like.

    Args:
        - o: Object to test.


    This function returns True if `KeyError` is raised when attempting
    to "key" the object with one it does not contain. The object
    must also implement or inherit the `__len__`, `__iter__`, and
    `__contains__` methods.

    Note that this function only tests/inspects behavior methods,
    and may return True even if an object does implement high-level
    `Mapping` methods such as `.get`.
    """
    # Could also throw it a non-hashable and check for `TypeError`, but
    # it feels more ambiguous than `KeyError` in this context.
    try:
        o[__key]
    except KeyError: pass
    except:
        return False
    return (
        hasattr(o, '__len__')
        and
        hasattr(o, '__contains__')
        and
        hasattr(o, '__iter__')
    )


def is_sequence(o: Any) -> bool:
    """Return True if an object implements the basic behavior of a
    sequence.

    Useful to validate an object based on protocol rather than type;
    objects need not be derived from `Sequence` to be considered a
    sequence or sequence-like.

    Args:
        - o: Object to test.


    This function returns True if `IndexError` is raised when attempting
    to "key" the object with an index outside of its' range. The object
    must also implement or inherit the `__len__`, `__iter__`, and
    `__contains__` methods.

    Note that this function only tests/inspects behavior methods,
    and may return True even if an object does implement high-level
    `Sequence` methods such as `.count` and `.index`.
    """
    try:
        o[len(o)]
    except IndexError: pass
    except:
        return False
    return hasattr(o, '__contains__') and hasattr(o, '__iter__')




# [Misc]

def rotate_array(arr: Any, npos: int):
    """Offset the contents of an array-like object by a set number of
    positions in-place, and return the array.

    Args:
        - arr: List-like object to rotate.

        - npos: Integer indicating the positional offset for *arr*s
        contents.


    *arr* must be a mutable sequence that supports slicing.

    A positive *npos* value rotates contents to the right -- toward the
    tail end -- of the array, while a negative value does the opposite.
    """
    arr_len = len(arr)
    if arr_len == 0:
        return arr

    npos = -npos % arr_len  # use `deque.rotate` sign convention, which differs from slicing
    arr[:] = arr[npos:arr_len] + arr[:npos]
    return arr




# [Descriptors]

class classproperty(abstract.Property[_T_co]):
    """Creates class-bound, read-only properties.

    Once assigned to a class attribute, accessing the actual descriptor
    object can be difficult due to the binding. To do so, use the
    `inspect.getattr_static` function.
    """

    __slots__ = ()

    def __init__(self, fget: Callable[[Any], _T_co] | None = None, doc: str | None = None):
        super().__init__(fget, None, None, doc)

    @overload
    def __get__(self, inst: Any, cls: type[Any], /) -> _T_co: ...
    @overload
    def __get__(self, inst: Any, cls: None, /) -> Self: ...
    def __get__(self, inst: Any = None, cls: Any = None, /):
        if cls is None:
            return self
        try:
            return self.fget(cls)  # type: ignore
        except TypeError:
            raise AttributeError(f'{type(self).__name__!r} object has no getter') from None

    def setter(self, *args) -> NotImplementedError:
        raise NotImplementedError(f"{type(self).__name__!r} object does not support setters")

    def deleter(self, *args) -> NotImplementedError:
        raise NotImplementedError(f"{type(self).__name__!r} object does not support deleters")


class cachedproperty(abstract.Property[_T_co]):
    """Alternative implementation of `functools.cached_property` that supports
    objects without managed dictionaries and allows for the registration of
    a "deleter" method.

    For normal classes, using `cachedproperty` is near identical to
    `functools.cached_property`:
        >>> class Object:
        ...
        ...     @cachedproperty
        ...     def some_expensive_property(self):
        ...         ...  # do stuff
        ...         return 5
        ...
    """
    __slots__ = ("_lock", "_name", "_getattr", "_setattr")

    def __init__(self, fget: Callable[[Any], _T_co] | None = None, fdel: Callable[[Any], Any] | None = None, doc: str | None = None, *, name: str = ''):
        super().__init__(fget, None, fdel, doc)
        self._name = name
        self._lock = threading.RLock()

    def __set_name__(self, cls: type[Any], name: str):
        if not managed_dict_type(cls):
            if not self._name:
                self._name = self.to_slot_name(name)

            if not isinstance(getattr(cls, self._name, None), types.MemberDescriptorType):
                msg = (
                    f"class {cls.__name__!r} is slotted and must define or inherit "
                    f"{self._name!r} slot member for {type(self).__name__!r} object {name!r}."
                )
                raise TypeError(msg)

            self._getattr = getattr
            self._setattr = setattr

        elif not self._name:
            self._name = name
            self._getattr = self.__dict_getter
            self._setattr = self.__dict_setter

    def __getstate__(self):
        return super().__getstate__()[0], {
            '_name'   : self._name,
            '_getattr': self._getattr,
            '_setattr': self._setattr,
        }

    def __setstate__(self, state):
        super().__setstate__(state)
        self._lock = threading.RLock()

    @overload
    def __get__(self, inst: Any, cls: type[Any] | None) -> _T_co: ...
    @overload
    def __get__(self, inst: None, cls: type[Any] | None) -> Self: ...
    def __get__(self, inst: Any, cls: Any = None, *, __missing=object()):
        if inst is None:
            return self

        try:
            value = self._getattr(inst, self._name, __missing)
        except AttributeError:
            raise RuntimeError(
                f"`__set_name__` method of {type(self).__name__!r} object was not called"
            ) from None

        if value is __missing:
            with self._lock:
                # check if the value was set while awaiting the lock
                value = self._getattr(inst, self._name, __missing)
                if value is __missing:
                    try:
                        value = self.fget(inst)  # type: ignore
                    except TypeError:
                        if self.fget is None:
                            raise TypeError(f"{type(self).__name__!r} object has no getter") from None
                        raise
                    self._setattr(inst, self._name, value)
        return value

    def __call__(self, fget: Callable[[Any], _T_co]):
        return self.getter(fget)

    def __dict_getter(self, inst, attr, default):
        return inst.__dict__.get(attr, default)

    def __dict_setter(self, inst, attr, value):
        inst.__dict__[attr] = value

    def setter(self, *args) -> NotImplementedError:
        raise NotImplementedError(f"{type(self).__name__!r} object does not support setters")

    @staticmethod
    def to_slot_name(name: str) -> str:
        """Get the expected private name of a attribute.

        This method is called in `__set_name__` when instances of *cls* are
        not expected to have a '__dict__' attribute (e.g. slotted classes)
        and when the *name* keyword is not included when the property was
        initialized.

        The default implementation simply returns *name* but prefixed with a
        single underscore (as per the typical "pythonic" convention for "private"
        members). Users can override this method via a subclass to fit their
        own needs.
        """
        return f"_{name}"



