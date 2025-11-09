param(
  [string]$Repo = "E:\PY_Pojekte\CrazyCar-Simulation"
)

$srcPkg   = Join-Path $Repo "src\crazycar"
$buildPkg = Join-Path $Repo "build\_cffi\crazycar"

# 1) Stale DLLs im Paket entfernen (Quelle von „falsche DLL geladen“)
Remove-Item "$srcPkg\carsim_native*.pyd","$srcPkg\carsim_native*.lib","$srcPkg\carsim_native*.exp" -Force -ErrorAction SilentlyContinue

# 2) Neu bauen (mit voller cdef)
python "$Repo\src\crazycar\interop\build_tools.py"

# 3) Symbolprobe
$env:PYTHONPATH = "$Repo\src"
python -c "import importlib; m=importlib.import_module('crazycar.carsim_native'); \`\
print('DLL:', m.__file__); lib=m.lib; \`\
print({n:hasattr(lib,n) for n in ('getfahr','fahr','getservo','servo','regelungtechnik','getfwert','getswert','getabstandvorne','getabstandrechts','getabstandlinks')})"
