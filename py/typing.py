try:
    from typing_extensions import *
except ImportError:
    raise ImportError("`typing-extensions` package required")
from typing import *
import os
import datetime
import array
import types
import pathlib

if TYPE_CHECKING:
    from numpy import (  # type: ignore
        generic as _np_generic,
        ndarray as _np_ndarray,
        dtype as _np_dtype,
    )
else:  # avoid stringification w/`import __future__.annotations`
    _np_generic = "_np_generic"
    _np_ndarray = "_np_ndarray"




# [ General TypeVars ]

T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)
T_contra = TypeVar("T_contra", contravariant=True)
KT = TypeVar("KT")
KT_co = TypeVar("KT_co", covariant=True)
KT_contra = TypeVar("KT_contra", contravariant=True)
VT = TypeVar("VT")
VT_co = TypeVar("VT_co", covariant=True)
CallableT = TypeVar('CallableT', bound=Callable)




# [ Structural Types ]

class SupportsRichComparison(Protocol):
    __slots__ = ()
    def __le__(self, other: Any, /) -> bool: ...
    def __lt__(self, other: Any, /) -> bool: ...
    def __eq__(self, other: Any, /) -> bool: ...
    def __gt__(self, other: Any, /) -> bool: ...
    def __ge__(self, other: Any, /) -> bool: ...

SupportsRichComparisonT = TypeVar('SupportsRichComparisonT', bound=SupportsRichComparison)


class SupportsStrCast(Protocol):
    __slots__ = ()
    def __str__(self) -> str: ...

SupportsStrCastT = TypeVar("SupportsStrCastT", bound=SupportsStrCast)


class SupportsIntCast(Protocol):
    __slots__ = ()
    def __int__(self) -> int: ...

SupportsIntCastT = TypeVar("SupportsIntCastT", bound=SupportsIntCast)


class SupportsBytesCast(Protocol):
    __slots__ = ()
    def __bytes__(self) -> bytes: ...

SupportsBytesCastT = TypeVar("SupportsBytesCastT", bound=SupportsBytesCast)


class SupportsSlice(Protocol[T_co]):
    __slots__ = ()
    def __getitem__(self, __slice: slice) -> Iterable[T_co]: ...

SupportsSliceT = TypeVar('SupportsSliceT', bound=SupportsSlice)


class SupportsView(Protocol[KT_co, VT_co]):
    __slots__ = ()
    def keys(self) -> Iterable[KT_co]: ...
    def values(self) -> Iterable[VT_co]: ...
    def items(self) -> Iterable[tuple[KT_co, VT_co]]: ...

SupportsViewT = TypeVar("SupportsViewT", bound=SupportsView)


class SupportsRead(Protocol[T_co]):
    __slots__ = ()
    def read(self) -> T_co: ...

SupportsReadT = TypeVar("SupportsReadT", bound=SupportsRead)


class SupportsWrite(Protocol[T_contra]):
    __slots__ = ()
    def write(self, obj: T_contra, /) -> Any: ...

SupportsWriteT = TypeVar("SupportsWriteT", bound=SupportsWrite)


class SupportsSend(Protocol[T_contra]):
    __slots__ = ()
    def send(self, obj: T_contra, /) -> Any: ...

SupportsSendT = TypeVar("SupportsSendT", bound=SupportsSend)


class SupportsRecv(Protocol):
    __slots__ = ()
    def recv(self) -> Any: ...

SupportsRecvT = TypeVar("SupportsRecvT", bound=SupportsRecv)


class Descriptor(Protocol[T_co]):
    __slots__ = ()
    @overload
    def __get__(self, __inst: None, __type: type[Any] | None) -> Self: ...
    @overload
    def __get__(self, __inst: T, __type: type[T] | None) -> T_co: ...

DescriptorT = TypeVar("DescriptorT", bound=Descriptor)


class DataDescriptor(Protocol[T_co, T_contra]):
    __slots__ = ()
    @overload
    def __get__(self, __inst: None, __type: type[Any] | None) -> Self: ...
    @overload
    def __get__(self, __inst: T, __type: type[T] | None) -> T_co: ...
    def __set__(self, __inst: Any, __value: T_contra) -> None: ...

DataDescriptorT = TypeVar("DataDescriptorT", bound=DataDescriptor)


class SizedArray(Protocol[T]):
    __slots__ = ()
    def __len__(self) -> int: ...
    def __iter__(self) -> Iterator[T]: ...
    @overload
    def __getitem__(self, __index: SupportsIndex, /) -> T: ...
    @overload
    def __getitem__(self, __slice: slice, /) -> Self: ...
    @overload
    def __setitem__(self, __key: SupportsIndex, __value: T, /) -> None: ...
    @overload
    def __setitem__(self, __key: slice, __value: Iterable[T], /) -> None: ...
    def __contains__(self, __key: Any, /) -> bool: ...

SizedArray.register(list)         # type: ignore
SizedArray.register(array.array)  # type: ignore
SizedArray.register(tuple)        # type: ignore

SizedArrayT = TypeVar('SizedArrayT', bound=SizedArray)




# [ Aliases ]

Mappable = TypeAliasType("Mappable", Mapping[KT, VT] | Iterable[tuple[KT, VT]], type_params=(KT, VT))
Array = array.ArrayType
StrPath = str | pathlib.Path
PathLike = os.PathLike
MappingProxy = types.MappingProxyType
Function = types.FunctionType
Method = types.MethodType
Module = types.ModuleType
Date = datetime.date
Time = datetime.time
DateTime = datetime.datetime

_NpDataType = TypeVar("_NpDataType", bound=_np_generic)
# ndarray-like
Vector = TypeAliasType('Vector', '_np_ndarray[tuple[_NpDataType], _np_dtype[_NpDataType]] | SizedArray[_NpDataType]', type_params=(_NpDataType,))
Matrix = TypeAliasType('Matrix', '_np_ndarray[tuple[_NpDataType, _NpDataType], _np_dtype[_NpDataType]] | SizedArray[Vector[_NpDataType]]', type_params=(_NpDataType,))
Tensor = TypeAliasType('Tensor', '_np_ndarray[tuple[_NpDataType, _NpDataType, _NpDataType], _np_dtype[_NpDataType]] | SizedArray[Matrix[_NpDataType]]', type_params=(_NpDataType,))



# [ Utilities ]

_MISSING = object()


@overload
def cast_to(tp: type[T]) -> Callable[[Any], T]: ...
@overload
def cast_to(tp: CallableT) -> Callable[[Any], CallableT]: ...
@overload
def cast_to(tp: type[T], value: Any) -> T: ...
@overload
def cast_to(tp: CallableT, value: Any) -> CallableT: ...
def cast_to(tp: Any, value: Any = _MISSING) -> Any:
    """Equivelent to `typing.cast` but can be used as a decorator."""
    if value is _MISSING:
        return lambda value: value
    return value
