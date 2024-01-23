from typing import *
from os import PathLike as PathLike
import datetime
import sys
import array
import types
import pathlib
if sys.version_info < (3, 12):
    from typing_extensions import Buffer as _Buffer, TypeAliasType as TypeAliasType
else:
    from collections.abc import Buffer as _Buffer
    from typing import TypeAliasType


_T = TypeVar("_T")
_T_co = TypeVar("_T_co", covariant=True)
_T_contra = TypeVar("_T_contra", contravariant=True)




# Generic `Buffer` protocol. Type checkers (pyright, at least) will
# not validate the inner type though, so this only improves type
# visibility in a literal sense (i.e. a person reading the code).
Buffer = TypeAliasType("Buffer", _Buffer, type_params=(_T,))
Array = array.ArrayType
StrPath = str | pathlib.Path
MappingProxy = types.MappingProxyType
Function = types.FunctionType
Method = types.MethodType
Date = datetime.date
Time = datetime.time
DateTime = datetime.datetime


class Descriptor(Protocol[_T_co]):
    @overload
    def __get__(self, __inst: None, __type: type[Any] | None) -> Self: ...
    @overload
    def __get__(self, __inst: _T, __type: type[_T] | None) -> _T_co: ...

class DataDescriptor(Protocol[_T_co, _T_contra]):
    @overload
    def __get__(self, __inst: None, __type: type[Any] | None) -> Self: ...
    @overload
    def __get__(self, __inst: _T, __type: type[_T] | None) -> _T_co: ...
    def __set__(self, __inst: Any, __value: _T_contra) -> None: ...


class Slicable(Protocol[_T_co]):
    def __getitem__(self, __slice: slice) -> Iterable[_T_co]: ...

Slicable.register(list)         # type: ignore
Slicable.register(array.array)  # type: ignore
Slicable.register(tuple)        # type: ignore
