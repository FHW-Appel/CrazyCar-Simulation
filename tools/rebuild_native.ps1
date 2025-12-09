<#
.SYNOPSIS
    Rebuild native C extension and verify exported symbols.

.DESCRIPTION
    Cleans stale DLLs from package directory, rebuilds the carsim_native extension
    using CFFI, and verifies that all required symbols are exported.

.PARAMETER Repo
    Path to repository root (default: E:\PY_Pojekte\CrazyCar-Simulation)

.EXAMPLE
    .\rebuild_native.ps1
    .\rebuild_native.ps1 -Repo "C:\Projects\CrazyCar-Simulation"
#>
param(
  [string]$Repo = "E:\PY_Pojekte\CrazyCar-Simulation"
)

$srcPkg   = Join-Path $Repo "src\crazycar"
$buildPkg = Join-Path $Repo "build\_cffi\crazycar"

# 1) Remove stale DLLs from package (source of "wrong DLL loaded" errors)
Remove-Item "$srcPkg\carsim_native*.pyd","$srcPkg\carsim_native*.lib","$srcPkg\carsim_native*.exp" -Force -ErrorAction SilentlyContinue

# 2) Build with full cdef
python "$Repo\src\crazycar\interop\build_tools.py"

# 3) Symbol verification
$env:PYTHONPATH = "$Repo\src"
python -c "import importlib; m=importlib.import_module('crazycar.carsim_native'); \`\
print('DLL:', m.__file__); lib=m.lib; \`\
print({n:hasattr(lib,n) for n in ('getfahr','fahr','getservo','servo','regelungtechnik','getfwert','getswert','getabstandvorne','getabstandrechts','getabstandlinks')})"
