"""A simple cx_Freeze setup script template.

How to use this script:
    1) add this file to your project directory
    2) install cx_Freeze ('python -m pip install cx_Freeze' via bash/terminal/powershell)
    3) fill out the 'BUILD SCRIPT SETUP' section below
    4) invoke the script from bash/terminal/powershell via 'python setup.py build'
"""
from typing import TypedDict, Sequence, Literal
from cx_Freeze import setup as _setup, Executable



WIN32GUI = "Win32GUI"
CONSOLE  = "console"


class MetaData(TypedDict, total=False):
    name            : str  # [REQUIRED]: project or application name
    version         : str  # [REQUIRED]: project version (ex. '0.1', '1.5.36')
    author          : str | None
    author_email    : str | None
    maintainer      : str | None
    url             : str | None
    description     : str | None
    long_description: str | None
    download_url    : str | None
    classifiers     : Sequence[str] | None
    platforms       : Sequence[str] | None
    keywords        : Sequence[str] | None
    license         : str | None


class BuildOpts(TypedDict, total=False):
    build_exe           : str | None               # defaults to './/build//exe.[platform identifier].[python version]'
    optimize            : Literal[0, 1, 2] | None  # optimization level -- 0 == 'disabled', 2 can brick app execution
    # NOTE: cx_Freeze will *try* to follow imports of code used by the target script,
    #       so manually including modules is not always necessary.
    excludes            : Sequence[str] | None     # list of module names to exclude
    includes            : Sequence[str] | None     # list of module names to include
    packages            : Sequence[str] | None     # list of package names to include, i.e. all modules/sub-packages in the namespace
    include_files       : Sequence[str] | None     # list of paths pointing to other files/folders to include in the output dir
    include_msvcr       : bool | None              # `True` auto-includes `vcruntime.dll` from 'C://Windows//System32'
    # niche options
    replace_paths       : Sequence[str] | None
    path                : Sequence[str] | None
    no_compress         : bool | None
    constants           : str | None
    bin_includes        : Sequence[str] | None
    bin_excludes        : Sequence[str] | None
    bin_path_includes   : Sequence[str] | None
    bin_path_excludes   : Sequence[str] | None
    zip_includes        : Sequence[str] | None
    zip_include_packages: Sequence[str] | None
    zip_exclude_packages: Sequence[str] | None
    silent              : str | None
    silent_level        : str | None



def setup(metadata: MetaData, build_options: BuildOpts, *exec_options: Executable):
    return _setup(**metadata, options={'build_exe': build_options}, executables=exec_options)




# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ BUILD SCRIPT SETUP ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

METADATA = MetaData(
    name='',
    version='',
)

BUILD_OPTS = BuildOpts(
    packages=[],
    includes=[],
    include_files=[],
    include_msvcr=True,
    optimize=0,
)

EXEC_OPTS: Sequence[Executable] = [
    Executable(
        # script [REQUIRED]: name of top-level module/script (must incl `.py`)
        script='',
        # icon: filepath to a '.ico' file to use as the executable icon
        icon=None,
        # base: should be 'Win32GUI' for win32 ui applications, otherwise 'console' or `None`
        base=None,
        # target_name: filename of created executable (must incl '.exe') -- defaults to *script* name
        target_name=None,
    ),
]




if __name__ == '__main__':
    setup(METADATA, BUILD_OPTS, *EXEC_OPTS)
