import sys
from typing import *
from os import PathLike as PathLike
from array import array as array
from types import (
    MappingProxyType as MappingProxyType,
    FunctionType as FunctionType,
    MethodType as MethodType,
)

if sys.version_info < (3, 12):
    from typing_extensions import Buffer as _Buffer, TypeAliasType
else:
    from collections.abc import Buffer as _Buffer
    from typing import TypeAliasType


_T = TypeVar("_T")
_G = TypeVar("_G", covariant=True)
_S = TypeVar("_S", contravariant=True)




# Generic `Buffer` protocol. Type checkers (pyright, at least) will
# not validate the inner type though, so this only improves type
# visibility in a literal sense (i.e. a person reading the code).
Buffer = TypeAliasType("Buffer", _Buffer, type_params=(_T,))


class Descriptor(Protocol[_G]):
    @overload
    def __get__(self, __inst: None, __type: type[Any] | None) -> Self: ...
    @overload
    def __get__(self, __inst: _T, __type: type[_T] | None) -> _G: ...

class DataDescriptor(Protocol[_G, _S]):
    @overload
    def __get__(self, __inst: None, __type: type[Any] | None) -> Self: ...
    @overload
    def __get__(self, __inst: _T, __type: type[_T] | None) -> _G: ...
    def __set__(self, __inst: Any, __value: _S) -> None: ...
