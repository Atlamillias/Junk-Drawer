<#
Python Virtual Environment Setup Script

This script was written for use with pyenv-win (https://github.com/pyenv-win/pyenv-win),
Visual Studio Code (https://code.visualstudio.com/), and the Project Templates VSCode
extension (https://marketplace.visualstudio.com/items?itemName=cantonios.project-templates).

Quick Tutorial:
    1A) Set up a project templates template(s) by creating a new folder within
    `<VSCode-data-folder>/user-data/User/ProjectTemplates`. Once created, create
    an inner '.scripts' folder. Move this script to the new '.scripts' folder.

    1B [optional]): Create one or more PIP requirements files containing "global"
    dependencies within the ProjectTemplates root folder. Dependencies listed
    in these files will be installed for any virtual environment created by
    the script regardless of the project.

    2A) In Visual Studio Code, open a repository/project folder. Then, open the
    Command Palette (keybound to `F1` and/or `Ctrl + Shift + P`) and use the
    "Project: Create Project from Template" command. Select the previously-
    created template folder.

    2B [optional]): Within the project's '.scripts' folder indicate the target
    Python version by doing ONE of the following:

        * Create a new file named `python<version>`, where `<version>` target
        Python version -- major, minor, and patch (optional) numbers ("python3.10",
        "python3.9.7", etc).

        * Within the `venv-setup.ps1` script, update the value of the `$pyVersion`
        variable (the very first line of actual code in the script) with the target
        version number ("3.10", "3.9.7", etc).

        If the minor patch number is omitted, the script will automatically use newest
        patch for that version.

    2C [optional]): Create one or more PIP requirements files containing the project
    dependencies within the project folder. These will be installed first, before
    installing "global" dependencies (see step 1B).

    3) Run `venv-setup.ps1` (located within the project's '.scripts' folder)
    as a PowerShell script. Doing so will create a virtual environment in the
    project's ".venv" folder. If a venv already exists within the folder, it
    is removed and a new one is created. If the Python/PyLance extension is
    installed, it will automatically detect the new environment and prompt you
    to set it for the project.

Notes:
    * PIP requirements files should be named "*requirements.txt" or "*requirements.text"
    e.g. "requirements.text", "dev-requirements.txt", etc.

    * Other variables aside from `$PyVersion` can be changed for other template/project
    structures.

#>


[string]$PyVersion = ""

$SCRIPT_FOLDER = '.scripts'
$PYVENV_FOLDER = '.venv'

$PYENV_ROOT  = "C:\Users\$env:UserName\.pyenv"
$VSDATA_ROOT = "$env:VSCODE_PORTABLE"





function IsNullString {
    param ([string]$s)
    return ([string]::IsNullOrEmpty($s) -or [string]::IsNullOrWhiteSpace($s))
}

function PyVersionFromFile {
    $fpath = (Get-ChildItem "$ROOT_DIR/$SCRIPT_FOLDER" -Name -Filter python*)

    if ($null -eq $fpath) {
        return ""
    }

    if ($fpath -is [System.Array]) {
        $fpath = $fpaths[0]
    }
    return $fpath.TrimStart('python')
}

function PyEnvLatest { param ([string]$version = "")
    if ($version) {
        return (pyenv install -l | findstr $version).Split(" ")[-1]
    }
    else {
        return (pyenv install -l).Split(" ")[-1]
    }
}



# [Script Setup]

if ([string]::IsNullOrEmpty($PSScriptRoot)) {   # allows for easier debugging in PS repl
    if ((Test-Path -Path "$PWD\$SCRIPT_FOLDER") -eq $false) {
        throw "Invalid folder structure -- working directory must contain a `"$SCRIPT_FOLDER`" folder."
    }

    Set-Variable ROOT_DIR -Option ReadOnly -Value "$PWD"
}
else {
    if (($PSScriptRoot -match "$SCRIPT_FOLDER$") -eq $false) {
        throw "Invalid folder structure -- script must be in a folder named `"$SCRIPT_FOLDER`"."
    }

    Set-Variable ROOT_DIR -Option ReadOnly -Value "$PSScriptRoot\.."
}

$env:Path = "$PYENV_ROOT/pyenv-win/shims;$PYENV_ROOT/pyenv-win/bin" + $env:Path  # pyenv search paths



# [Script]

if (IsNullString($PyVersion)) {

    $PyVersion = (PyVersionFromFile)

    if (IsNullString($PyVersion)) {
        $PyVersion = (PyEnvLatest $PyVersion)
        New-Item "$ROOT_DIR/python$PyVersion" -type file
    }
    elseif ($PyVersion -ne ($_PyVersion = PyEnvLatest $PyVersion)) {
        $PyVersion = $_PyVersion
        Remove-Item "$ROOT_DIR/$SCRIPT_FOLDER/python*"
        New-Item "$ROOT_DIR/$SCRIPT_FOLDER/python$PyVersion" -type file
    }
}

pyenv install $PyVersion "--skip-existing"
pyenv shell $PyVersion

Write-Host "Creating virtual environment..."
python -m venv --clear --upgrade-deps "$ROOT_DIR/$PYVENV_FOLDER"
pyenv shell --unset

& "$ROOT_DIR/$PYVENV_FOLDER/Scripts/Activate.ps1"

Write-Host 'Installing dependencies...'
foreach ($p in Get-ChildItem "$ROOT_DIR\*requirements.t*") {
    & "pip" "install" "-r" "`"$p`""
}
foreach ($p in Get-ChildItem "$VSDATA_ROOT\user-data\User\ProjectTemplates\*requirements.t*") {
    & "pip" "install" "-r" "`"$p`""
}