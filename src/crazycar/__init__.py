# erlaubt Submodule auch aus build/_cffi/crazycar zu laden
import os
_build_pkg = os.path.join(os.path.dirname(__file__), '..', '..', 'build', '_cffi', 'crazycar')
_build_pkg = os.path.normpath(os.path.abspath(_build_pkg))
if os.path.isdir(_build_pkg) and _build_pkg not in __path__:
    __path__.append(_build_pkg)
