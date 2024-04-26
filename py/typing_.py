from typing import *  # type: ignore
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
_KT = TypeVar("_KT")
_VT = TypeVar("_VT")
_T_co = TypeVar("_T_co", covariant=True)
_T_contra = TypeVar("_T_contra", contravariant=True)




# Generic `Buffer` protocol. Type checkers (pyright, at least) will
# not validate the inner type though, so this only improves type
# visibility in a literal sense (i.e. a person reading the code).
Buffer = TypeAliasType("Buffer", _Buffer, type_params=(_T,))
Mappable = TypeAliasType("Mappable", Mapping[_KT, _VT] | Sequence[tuple[_KT, _VT]], type_params=(_KT, _VT))
Array = array.ArrayType
StrPath = str | pathlib.Path
MappingProxy = types.MappingProxyType
Function = types.FunctionType
Method = types.MethodType
Date = datetime.date
Time = datetime.time
DateTime = datetime.datetime




class SupportsRichComp(Protocol):
    __slots__ = ()
    def __le__(self, other: Any, /) -> bool: ...
    def __lt__(self, other: Any, /) -> bool: ...
    def __eq__(self, other: Any, /) -> bool: ...
    def __gt__(self, other: Any, /) -> bool: ...
    def __ge__(self, other: Any, /) -> bool: ...


class Descriptor(Protocol[_T_co]):
    __slots__ = ()
    @overload
    def __get__(self, __inst: None, __type: type[Any] | None) -> Self: ...
    @overload
    def __get__(self, __inst: _T, __type: type[_T] | None) -> _T_co: ...

class DataDescriptor(Protocol[_T_co, _T_contra]):
    __slots__ = ()
    @overload
    def __get__(self, __inst: None, __type: type[Any] | None) -> Self: ...
    @overload
    def __get__(self, __inst: _T, __type: type[_T] | None) -> _T_co: ...
    def __set__(self, __inst: Any, __value: _T_contra) -> None: ...


class Slicable(Protocol[_T_co]):
    __slots__ = ()
    def __getitem__(self, __slice: slice) -> Iterable[_T_co]: ...

Slicable.register(list)         # type: ignore
Slicable.register(array.array)  # type: ignore
Slicable.register(tuple)        # type: ignore


class SizedArray(Protocol[_T]):
    __slots__ = ()
    def __len__(self) -> int: ...
    def __iter__(self) -> Iterator[_T]: ...
    @overload
    def __getitem__(self, __index: SupportsIndex, /) -> _T: ...
    @overload
    def __getitem__(self, __slice: slice, /) -> 'SizedArray[_T]': ...
    @overload
    def __setitem__(self, __key: SupportsIndex, __value: _T, /) -> None: ...
    @overload
    def __setitem__(self, __key: slice, __value: Iterable[_T], /) -> None: ...
    def __contains__(self, __key: Any, /) -> bool: ...

SizedArray.register(list)         # type: ignore
SizedArray.register(array.array)  # type: ignore
SizedArray.register(tuple)        # type: ignore



try:
    import numpy as np  # type: ignore

    _NpDataType = TypeVar("_NpDataType", bound=np.generic)

    Vector = TypeAliasType('Vector', np.ndarray[tuple[_NpDataType], np.dtype[_NpDataType]] | SizedArray[_NpDataType], type_params=(_NpDataType,))
    Matrix = TypeAliasType('Matrix', np.ndarray[tuple[_NpDataType, _NpDataType], np.dtype[_NpDataType]] | SizedArray[Vector[_NpDataType]], type_params=(_NpDataType,))
    Tensor = TypeAliasType('Tensor', np.ndarray[tuple[_NpDataType, _NpDataType, _NpDataType], np.dtype[_NpDataType]] | SizedArray[Matrix[_NpDataType]], type_params=(_NpDataType,))
except ImportError:
    pass
