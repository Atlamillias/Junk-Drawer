import sys
import enum
import types
from typing import overload, Any, Generic, Mapping, Iterable, Callable, Sequence, TypeVar
try:
    from typing_extensions import Self
except ImportError:
    from typing import Self




T = TypeVar("T")




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


_DEFAULT_MODULE = create_module('')

def create_function(
    name       : str,
    args       : Sequence[str],
    body       : Sequence[str],
    return_type: T = Any,
    module     : str = '',
    *,
    globals    : dict[str, Any] | None = None,
    locals     : Mapping[str, Any] | Iterable[tuple[str, Any]] = ()
) -> Callable[..., T]:
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
            globals = _DEFAULT_MODULE.__dict__

    closure = (
        f"def __create_function__({', '.join(locals)}):\n"
        f"    def {name}({', '.join(args)}) -> _return_type:\n{body}\n"
        f"    return {name}"
    )

    scope = {}
    exec(closure, globals, scope)

    fn = scope["__create_function__"](**locals)
    fn.__module__   = module or _DEFAULT_MODULE.__name__
    fn.__qualname__ = fn.__name__ = name

    return fn


@overload
def is_builtin(o: Any) -> bool: ...  # type: ignore
def is_builtin(o: Any, *, __module=type.__module__) -> bool:
    """Return True if an object is a built-in function or class.

    Unlike `inspect.isbuiltin`, the result of this function is not falsified
    by C-extension objects, and can also identify built-in classes.
    """
    try:
        return o.__module__ == __module
    except:
        return False


def is_cfunction(o: Any) -> bool:
    """Return True if an object is a function implemented in C. This
    includes built-in functions like `len` and `isinstance`, as well
    as those exported in C-extensions.
    """
    return isinstance(o, types.BuiltinFunctionType)


@overload
def is_mapping(o: Any) -> bool: ...  # type: ignore
def is_mapping(o: Any, *, __key=object(), __members=('__len__', '__contains__', '__iter__')):
    """Return True if an object has a `__getitem__` method that can raise
    `KeyError`, while also implementing or inheriting the `__len__`,
    `__iter__`, and `__contains__` methods.
    """
    try:
        o[__key]
    except KeyError: pass
    except:
        return False
    return all(hasattr(o, m) for m in __members)


@overload
def is_sequence(o: Any) -> bool: ...  # type: ignore
def is_sequence(o: Any, *, __key=object(), __members=('__len__', '__contains__', '__iter__')):
    """Return True if an object has a `__getitem__` method that can raise
    `IndexError`, while also implementing or inheriting the `__len__`,
    `__iter__`, and `__contains__` methods.
    """
    try:
        o[__key]
    except IndexError: pass
    except:
        return False
    return all(hasattr(o, m) for m in __members)




class _ClassPropertyType(type):
    # This metaclass manages `classproperty.__doc__` descriptor behavior;
    # allowing class and instance-level docstrings to exist despite being
    # a slotted class (adding `__doc__` to `__slots__` is a no-go).

    __slots__ = ()

    # class-level docstring (`classproperty.__doc__`)
    @property
    def __doc__(self) -> str | None:
        return getattr(self, '_class_docstring')
    @__doc__.setter
    def __doc__(self, value: str | None):
        setattr(self, '_class_docstring', value)

    def __new__(mcls, name, bases, namespace, **kwargs):
        namespace['_class_docstring'] = namespace.pop('__doc__', None)

        try:
            classproperty  # type: ignore
        except NameError:
            # The `classproperty` class is being built. VERY unlikely, but it may
            # have been built already but was deleted (by someone?)...
            assert len(_ClassPropertyType.__subclasses__(mcls)) == 0
            assert '__slots__' in namespace

            # instance-level docstring (`classproperty().__doc__`)
            namespace['__doc__'] = property(
                # Use the explicitly set docstring, falling back to the getter
                # docstring when empty.
                lambda self: getattr(self, '_inst_docstring', None) or getattr(self.fget, '__doc__', None),
                lambda self, v: setattr(self, '_inst_docstring', v)
            )
            namespace['__slots__'] = ['_inst_docstring', *namespace['__slots__']]

        return super().__new__(mcls, name, bases, namespace, **kwargs)

    def __instancecheck__(self, inst: Any) -> bool:
        return isinstance(inst, (property, classmethod))

    def __subclasscheck__(self, cls: Any) -> bool:
        return issubclass(cls, (property, classmethod))

class classproperty(Generic[T], metaclass=_ClassPropertyType):
    """Creates class-bound, read-only properties.

    Accessing the actual descriptor object can be difficult to the
    binding. To do so, use the `inspect.getattr_static` function.

    Note that all `classproperty` objects are virtual subclasses
    of the `property` and `classmethod` built-in classes.
    """

    __slots__ = ('fget', '_name')

    def __set_name__(self, cls: Any, name: str):
        self._name = name

    def __init__(self, fget: Callable[[Any], T] | None = None, doc: str | None = None):
        self.fget    = fget
        self.__doc__ = doc  # type: ignore

    def __getstate__(self):
        return (None, {m:getattr(self, m) for m in self.__slots__})

    def __copy__(self):
        p = type(self).__new__(type(self))
        for m, v in self.__getstate__()[1].items():
            setattr(p, m, v)
        return p

    def __replace__(self, **kwargs):
        p = self.__copy__()
        for m, v in kwargs.items():
            setattr(p, m, v)
        return p

    @property
    def __wrapped__(self):
        return self.fget

    @overload
    def __get__(self, inst: Any = ..., cls: None = ...) -> Self: ...
    @overload
    def __get__(self, inst: Any = ..., cls: type[Any] = ...) -> T: ...
    def __get__(self, inst: Any = None, cls: type[Any] | None = None):
        if cls is None:
            return self
        try:
            return self.fget(cls)  # type: ignore
        except TypeError:
            raise AttributeError(f'{type(self).__name__!r} object has no getter') from None

    def getter(self, fget: Callable[[Any], T]):
        p = self.__copy__()
        p.__init__(fget, self.__doc__)
        return p
