from typing import overload, Any, TypeVar, SupportsIndex, Hashable, Mapping, Sequence, Generic, Iterator, Callable, Self
import itertools
import threading
import contextlib
import collections.abc
import types
import sys
import abc




T    = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)
KT   = TypeVar("KT", bound=Hashable)
VT   = TypeVar("VT")

_MISSING = object()


# [Slotted Class Mixins]

class DenyManagedDict:
    """Mixin for slotted classes. Prevents subclass creation when instances
    of the resulting class would have a `__dict__` attribute; enforcing
    that `__slots__` be declared on all of its' user-defined parent classes.
    """
    __slots__ = ()

    def __init_subclass__(cls):
        has_inst_dict_flag = [b for b in cls.__bases__ if b.__flags__ & (1 << 4)]
        if has_inst_dict_flag:
            msg = (
                f"{cls.__name__} class leaks `Py_TPFLAG_MANAGED_DICT` from one or "
                f"more base classes ({', '.join(repr(b.__name__) for b in has_inst_dict_flag)})"
            )
            raise TypeError(msg)
        super().__init_subclass__()


class SlotState:
    """Mixin class with a `_slot_members_` classmethod that returns a tuple
    containing the names of a subclass' slotted attributes; both declared and
    inherited from parent classes at the time of its' creation.

    Implements object state methods `__getstate__`, `__copy__`, and `__replace__`
    methods that target slot members.
    """
    __slots__ = ()

    __slot_members: tuple[str, ...]

    @classmethod
    def _slot_members_(cls):
        return cls.__slot_members

    def __init_subclass__(cls):
        super().__init_subclass__()
        # Inspecting the class-level `__slots__` is *usually* reliable, but
        # not always. `__slots__` can be almost any iterable, including
        # generators (which will be exhausted by the time of inspection).
        # Additionally, it may have been deleted after class creation. This
        # implementation is not 100% sound either, since members themselves
        # may also be deleted. This is why the mro is re-iterated with every
        # new subclass instead of relying on the `_slot_members_` of a parent
        # class which may become dirty in VERY rare cases.
        _seen = set()  # keep order
        cls.__slot_members = tuple(
            k for k, v in itertools.chain(
                *(_cls.__dict__.items() for _cls in cls.mro()[:-1])
            )
            if k not in _seen and
            isinstance(v, types.MemberDescriptorType) and not (_seen.add(k))
        )

    def __getstate__(self, *, __missing=object()):
        return (
            None,
            {
                m:v for m in type(self).__slot_members
                if (v:=getattr(self, m, __missing)) is not __missing
            }
        )

    def __copy__(self):
        p = self.__new__(type(self))
        for m, v in self.__getstate__()[1].items():
            setattr(p, m, v)
        return p

    def __replace__(self, **kwargs):
        p = self.__new__(type(self))
        state = self.__getstate__()[1]
        state.update(kwargs)
        for m, v in state.items():
            setattr(p, m, v)
        return p


class Slotted(SlotState, DenyManagedDict):
    """Mixin for slotted classes. Prevents subclass creation when instances
    of the resulting class would have a `__dict__` attribute; enforcing
    that `__slots__` be declared on all of its' base classes.

    Implements object state methods `__getstate__`, `__copy__`, and `__replace__`
    methods that target slot members. The class-level `_slot_members_` attribute
    contains the names of all slot members.
    """
    __slots__ = ()





# [Composition ABCs]

class Composed(Generic[T]):
    """Generic base class for objects operating on an underlying subscriptable
    container. Must implement an `_object_state_` method that returns a
    subscriptable container.
    """
    __slots__ = ()

    @abc.abstractmethod
    def _object_state_(self) -> Sequence[T]:
        """Must return the object's public state as a subscriptable container."""
        return NotImplemented

    def __contains__(self, __value: Any) -> bool:
        return __value in self._object_state_()

    def __getitem__(self, __key: Any) -> T:
        return self._object_state_()[__key]

    def __iter__(self) -> Iterator[T]:
        return iter(self._object_state_())

    def __len__(self) -> int:
        return len(self._object_state_())


class Keyed(Composed, Generic[KT, VT]):
    """Generic base class for iterables supporting hashable subscript.
    Must implement an `_object_state_` method that returns a map-like
    object."""
    __slots__ = ()

    __abc_tpflags__ = 1 << 6 # Py_TPFLAGS_MAPPING

    @abc.abstractmethod
    def _object_state_(self) -> Mapping[KT, VT]:
        """Must return the object's public state as a mapping."""
        return NotImplemented

    @overload
    def get(self, __key: KT, /) -> VT: ...
    @overload
    def get(self, __key: KT, __default: Any, /) -> VT | Any: ...
    def get(self, *args):
        return self._object_state_().get(*args)


class Mapped(Keyed[KT, VT]):
    """Generic base class for mapping-like objects. Must implement an
    `_object_state_` method that returns a map-like object."""
    __slots__ = ()

    def items(self):
        return collections.abc.ItemsView(self._object_state_())

    def keys(self):
        return collections.abc.KeysView(self._object_state_())

    def values(self):
        return collections.abc.ValuesView(self._object_state_())


class Indexed(Composed[T]):
    """Generic base class for iterables supporting zero-indexed subscript.
    Must implement an `_object_state_` method that returns a sequence-like
    object.
    """
    __slots__ = ()

    __abc_tpflags__ = 1 << 5 # Py_TPFLAGS_SEQUENCE

    @abc.abstractmethod
    def _object_state_(self) -> Sequence[T]:
        """Must return the object's public state as a mapping."""
        return NotImplemented

    def __getitem__(self, __index: SupportsIndex):
        return self._object_state_()[__index]

    def __reversed__(self) -> Iterator[T]:
        yield from reversed(self._object_state_())

    def index(self, __value: T, __start: int = 0, __stop: int = sys.maxsize, /) -> int:
        return self._object_state_().index(__value, __start, __stop)

    def count(self, __value: Any, /) -> int:
        return self._object_state_().count(__value)




# [Descriptors]

_PROPERTY_TYPE_INIT      = '_PropertyType__init'            # indicates instance docstrings of the "readying" class are writable
_PROPERTY_TYPE_INST_DOC  = '_PropertyType__inst_docstring'  # attrib containing the instance-level docstring
_PROPERTY_TYPE_CLASS_DOC = '_PropertyType__class_docstring' # attrib containing the class-level docstring

class _disabled_descriptor:
    __slots__ = ('cls', 'attrib', 'value', '_lock')

    def __init__(self, cls: Any, attrib: str):
        self.cls    = cls
        self.attrib = attrib
        self._lock  = threading.Lock()

    def __enter__(self):
        self.disable()
        return self

    def __exit__(self, *args):
        self.enable()

    def disable(self):
        self._lock.acquire()
        self.value = getattr(self.cls, self.attrib)
        # `delattr` doesn't work on metaclasses; or, at least not while
        # readying a new class with them.
        setattr(self.cls, self.attrib, None)

    def enable(self):
        setattr(self.cls, self.attrib, self.value)
        del self.value
        self._lock.release()


class PropertyType(type):
    """Metaclass that helps classes emulate the certain behaviors of
    the `property` builtin class. Allows slotted classes to have readable
    and writable instance-level and class-level docstrings.
    """
    # NOTE: The above docstring is not available at runtime!

    __slots__ = ()

    @property
    def __doc__(self) -> str | None:
        return getattr(self, _PROPERTY_TYPE_CLASS_DOC)
    @__doc__.setter
    def __doc__(self, value: str | None):
        setattr(self, _PROPERTY_TYPE_CLASS_DOC, value)
    @__doc__.deleter
    def __doc__(self):
        self.__doc__ = None

    def __new__(
        mcls,
        name,
        bases,
        namespace,
        **kwargs,
    ):
        # [once per inheritance tree] ensure that instance docstrings
        # will be writable
        if not any(hasattr(b, _PROPERTY_TYPE_INIT) for b in bases):
            if '__slots__' in namespace:
                namespace['__slots__'] = [*namespace['__slots__'], _PROPERTY_TYPE_INST_DOC]
            namespace[_PROPERTY_TYPE_CLASS_DOC] = namespace.pop('__doc__', None)
            namespace['__doc__'] = property(
                lambda self: getattr(self, _PROPERTY_TYPE_INST_DOC, None) or getattr(self.fget, '__doc__', None),
                lambda self, v: setattr(self, _PROPERTY_TYPE_INST_DOC, v),
            )
            namespace[_PROPERTY_TYPE_INIT] = True

            return super().__new__(mcls, name, bases, namespace, **kwargs)

        cls = super().__new__(mcls, name, bases, namespace, **kwargs)
        with _disabled_descriptor(PropertyType, '__doc__'):
            assert isinstance(cls.__doc__, (type(None), str))
            setattr(cls, _PROPERTY_TYPE_CLASS_DOC, cls.__doc__)
            del cls.__doc__  # Python-added `__doc__` overrides inherited descriptor
        return cls

    def __instancecheck__(self, inst: Any) -> bool:
        return isinstance(inst, property)

    def __subclasscheck__(self, cls: type) -> bool:
        return issubclass(cls, property)


class Property(Generic[T_co], metaclass=PropertyType):
    """A fully-extensible emulation of the built-in `property`
    class. Derived classes are considered subclasses of `property`.

    Unlike `property`, the `Property` class (and by extension, any
    subclass) is made generic to support typing. It also implements
    the `__replace__` and `__copy__` methods. These methods, in
    addition to several other non-descriptor methods, make use of the
    `__getstate__` and `__setstate__` hooks which can be overridden
    when need be.
    """

    __slots__ = ('_fget', '_fset', '_fdel')

    def __init__(
        self,
        fget: Callable[[Any], T_co] | None = None,
        fset: Callable[[Any, Any], Any] | None = None,
        fdel: Callable[[Any], Any] | None = None,
        doc : str | None = None
    ):
        self._fget   = fget
        self._fset   = fset
        self._fdel   = fdel
        self.__doc__ = doc   # type: ignore

    @property
    def fget(self):
        return self._fget

    @property
    def fset(self):
        return self._fset

    @property
    def fdel(self):
        return self._fdel

    def __getstate__(self) -> tuple[tuple[Callable | None, Callable | None, Callable | None, str | None], dict[str, Any] | None]:
        """Return the simplified state of this object.

        The value returned is a 2-tuple; one of Python's "default state" formats.
        The first item is another tuple containing (in order) `Property.__init__`
        positional arguments -- the state implemented by the `Property` class. The
        second item in the tuple is any "additional state" implemented via
        subclassing, which is None (default) or an "attribute-to-value" dictionary.
        """
        return (self.fget, self.fset, self.fdel, self.__doc__), None

    def __setstate__(self, state: tuple[tuple[Callable | None, Callable | None, Callable | None, str | None], dict[str, Any] | None]):
        """Update the object using from a simplified state.

        Args:
            - state: A 2-tuple, where the first item is a 4-tuple and the second
            is None or a "attribute-to-value" dictionary.


        When setting the object state, `Property.__init__` is (explicitly) called
        and receives values within the first item in *state*. If the second value
        is not None, it must be a dictionary -- `setattr` is used to update the
        object with the "attribute-to-value" pairs it contains.
        """
        Property.__init__(self, *state[0])
        if state[1] is not None:
            for k,v in state[1].items():
                setattr(self, k, v)

    def __copy__(self):
        p = self.__new__(type(self))
        p.__setstate__(self.__getstate__())
        return p

    # FIXME: The return types for overloads 1 & 2 should be equivelent to
    #        `type(self)[T]()` (different inner type)
    @overload
    def __replace__(self, *, fget: Callable[[Any], T], fset: Callable[[Any, Any], Any] | None = ..., fdel: Callable[[Any], Any] | None = ..., doc : str | None = ..., **kwargs) -> Self: ...
    @overload
    def __replace__(self, *, fget: None, fset: Callable[[Any, Any], Any] | None = ..., fdel: Callable[[Any], Any] | None = ..., doc : str | None = ..., **kwargs) -> Self: ...
    @overload
    def __replace__(self, *, fset: Callable[[Any, Any], Any] | None = ..., fdel: Callable[[Any], Any] | None = ..., doc : str | None = ..., **kwargs) -> Self: ...
    def __replace__(self, *, fget: Callable[[Any], T] | Any = _MISSING, fset: Any = _MISSING, fdel: Any = _MISSING, doc: Any = _MISSING, **kwargs):  # type: ignore
        # XXX: The `__replace__` method is considered a "standard" Python
        # behavior method as of Python 3.12.
        prop_state, user_state = self.__getstate__()
        prop_state = tuple(
            nv if nv is not _MISSING else ov
            for nv, ov in zip((fget, fset, fdel, doc), prop_state)
        )

        if kwargs:
            if user_state is None:
                user_state = {}
            user_state.update(kwargs)

        p = self.__new__(type(self))
        p.__setstate__((prop_state, user_state))  # type: ignore
        return p

    @overload
    def __get__(self, inst: Any, cls: type[Any] | None, /) -> T_co: ...
    @overload
    def __get__(self, inst: None, cls: type[Any] | None, /) -> Self: ...
    def __get__(self, inst: Any, cls: type[Any] | None = None):
        if inst is None:
            return self
        try:
            return self._fget(inst)  # type: ignore
        except TypeError:
            if self._fget is None:
                raise AttributeError(f'{type(self).__name__!r} object has no getter') from None
            raise

    def __set__(self, inst: Any, value: Any) -> None:
        try:
            self._fset(inst, value)  # type: ignore
        except TypeError:
            raise AttributeError(
                f"cannot set read-only attribute of {type(inst).__name__!r} object"
            ) from None

    def __delete__(self, inst: Any) -> None:
        try:
            self._fdel(inst)  # type: ignore
        except TypeError:
            raise AttributeError(f"cannot delete read-only attribute of {type(inst).__name__!r} object")

    def getter(self, fget: Callable[[Any], T]):
        return self.__replace__(fget=fget)

    def setter(self, fset: Callable[[Any, Any], Any]):
        return self.__replace__(fset=fset)

    def deleter(self, fdel: Callable[[Any], Any]):
        return self.__replace__(fdel=fdel)