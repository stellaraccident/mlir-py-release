#  Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.
#  See https://llvm.org/LICENSE.txt for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

# This setup.py file adapted from many places, including:
#   https://github.com/pytorch/pytorch/blob/master/setup.py
#   various places on stack overflow
#   IREE setup files
# (does anyone write these things except by copy-paste-mash-keys until it
# works?)

# This future is needed to print Python2 EOL message
from __future__ import print_function
import sys
if sys.version_info < (3,):
  print("Python 2 has reached end-of-life and is no longer supported.")
  sys.exit(-1)
if sys.platform == 'win32' and sys.maxsize.bit_length() == 31:
  print(
      "32-bit Windows Python runtime is not supported. Please switch to 64-bit Python."
  )
  sys.exit(-1)

import importlib
import platform
python_min_version = (3, 6, 2)
python_min_version_str = '.'.join(map(str, python_min_version))
if sys.version_info < python_min_version:
  print("You are using Python {}. Python >={} is required.".format(
      platform.python_version(), python_min_version_str))
  sys.exit(-1)

import json
import os
import pathlib
import subprocess
import shutil
import sysconfig

from distutils.command.install_data import install_data
from setuptools import setup, Extension, distutils, find_packages
from setuptools.command.build_ext import build_ext
from setuptools.command.install_lib import install_lib
from setuptools.command.install_scripts import install_scripts
from distutils import core
from distutils.core import Distribution
from distutils.errors import DistutilsArgError

################################################################################
# Parameters parsed from environment
################################################################################

is_windows = platform.system() == 'Windows'

VERBOSE_SCRIPT = True
RUN_BUILD_DEPS = True
# see if the user passed a quiet flag to setup.py arguments and respect
# that in our parts of the build
EMIT_BUILD_WARNING = False
RERUN_CMAKE = False
CMAKE_ONLY = False
filtered_args = []
for i, arg in enumerate(sys.argv):
  if arg == '--cmake':
    RERUN_CMAKE = True
    continue
  if arg == '--cmake-only':
    # Stop once cmake terminates. Leave users a chance to adjust build
    # options.
    CMAKE_ONLY = True
    continue
  if arg == "--":
    filtered_args += sys.argv[i:]
    break
  if arg == '-q' or arg == '--quiet':
    VERBOSE_SCRIPT = False
  filtered_args.append(arg)
sys.argv = filtered_args

if VERBOSE_SCRIPT:

  def report(*args):
    print('--', *args)
else:

  def report(*args):
    pass


def abort(*args):
  print('!! ERROR:', *args)
  sys.exit(1)


def get_setting(varname, default_value):
  value = os.environ.get(varname)
  if value is None:
    return default_value
  return value


def get_bool_setting(varname, default_value):
  value = get_setting(varname, default_value)
  if value is True or value is False:
    return value
  return value == '' or value == 'ON' or value == '1'


def which(thefile):
  path = os.environ.get("PATH", os.defpath).split(os.pathsep)
  for d in path:
    fname = os.path.join(d, thefile)
    fnames = [fname]
    if sys.platform == 'win32':
      exts = os.environ.get('PATHEXT', '').split(os.pathsep)
      fnames += [fname + ext for ext in exts]
    for name in fnames:
      if os.access(name, os.F_OK | os.X_OK) and not os.path.isdir(name):
        return name
  return None


def use_tool_path(toolname):
  value = get_setting(f'USE_{toolname.upper()}', 'ON')
  if value.upper() == 'OFF':
    return None
  if value.upper() == 'ON' or value == '':
    return which(toolname)
  if os.access(value, os.F_OK | os.X_OK) and not os.path.isdir(value):
    return value


################################################################################
# Build deps.
################################################################################
def check_py_dep(modulename, package):
  try:
    importlib.import_module(modulename)
  except ModuleNotFoundError:
    abort(
        f'Could not find required build-time module "{modulename}"\n'
        f'  (typically installed via "{sys.executable} -m pip install {package}")'
    )


check_py_dep('pybind11', 'pybind11')
check_py_dep('numpy', 'numpy')

################################################################################
# Figure out where we are and where we are going.
################################################################################
# report("Environment:")
# for env_key in os.environ:
#   report(f"  : {env_key} = {os.environ.get(env_key)}")
repo_root = os.path.abspath(
    get_setting('REPO_DIR', os.path.join(os.path.dirname(__file__), '..',
                                         '..')))
report(f'Using REPO_DIR = {repo_root}')
llvm_repo_dir = get_setting(
    'LLVM_REPO_DIR',
    os.path.abspath(os.path.join(repo_root, '..', 'llvm-project')))
report(f'Using LLVM_REPO_DIR = {llvm_repo_dir}')
if not os.path.isfile(os.path.join(llvm_repo_dir, 'llvm', 'CMakeLists.txt')):
  abort(f'Could not find LLVM sources in {llvm_repo_dir}')
build_dir = os.path.join(repo_root, 'build', 'llvm')
install_dir = os.path.join(repo_root, 'install', 'llvm')

################################################################################
# Load version_info.json
################################################################################

def load_version_info():
  with open(os.path.join(repo_root, 'version_info.json'), 'rt') as f:
    return json.load(f)
try:
  version_info = load_version_info()
except FileNotFoundError:
  version_info = {}

################################################################################
# Clean up CMakeCache.txt.
# This may seem counter-intuitive, but for a CI that may cycle through a
# couple of configurations, just clearing the cache between runs can let us
# get some incrementality to the artifacts while building for different
# python versions.
################################################################################

cmake_cache_file = os.path.join(build_dir, 'CMakeCache.txt')
if os.path.exists(cmake_cache_file):
  report('Removing existing CMakeCache.txt')

################################################################################
# CMake configure.
################################################################################
release_mode = get_bool_setting('RELEASE_MODE', True)
assertions = get_bool_setting('LLVM_ASSERTIONS', False)
stripped = '-stripped' if release_mode else ''

cmake_args = [
    f'-S{os.path.join(llvm_repo_dir, "llvm")}',
    f'-B{build_dir}',
    '-DCMAKE_CXX_VISIBILITY_PRESET=hidden',
    '-DCMAKE_VISIBILITY_INLINES_HIDDEN=ON',
    # We use private libs and special fixups to find everything.
    '-DCMAKE_PLATFORM_NO_VERSIONED_SONAME=ON',
    f'-DCMAKE_INSTALL_PREFIX={install_dir}',
    f'-DCMAKE_BUILD_TYPE={"Release" if release_mode else "RelWithDebInfo"}',
    f'-DLLVM_ENABLE_ASSERTIONS={"ON" if assertions else "OFF"}',
    '-DLLVM_TARGETS_TO_BUILD=host',
    '-DLLVM_ENABLE_PROJECTS=mlir',
    '-DMLIR_BINDINGS_PYTHON_ENABLED=ON',
    '-DMLIR_PYTHON_BINDINGS_VERSION_LOCKED=OFF',
    f'-DPython3_EXECUTABLE:FILEPATH={sys.executable}',
    f'-DPython3_INCLUDE_DIR:PATH={sysconfig.get_path("include")}',
]

cmake_targets = [
    # Headers.
    'install-mlir-headers',
    # Python bindings.
    'install-MLIRBindingsPythonSources',
    'install-MLIRBindingsPythonDialects',
    # C-API shared library/DLL.
    f'install-MLIRPublicAPI{stripped}',
    # Python extensions.
    f'install-MLIRTransformsBindingsPythonExtension{stripped}',
    f'install-MLIRCoreBindingsPythonExtension{stripped}',
]

### HACK: Add a Python3_LIBRARY because cmake needs it, but it legitimately
### does not exist on manylinux (or any linux static python).
# Need to explicitly tell cmake about the python library.
python_libdir = sysconfig.get_config_var('LIBDIR')
python_library = sysconfig.get_config_var('LIBRARY')
if python_libdir and not os.path.isabs(python_library):
  python_library = os.path.join(python_libdir, python_library)

# On manylinux, python is a static build, which should be fine, but CMake
# disagrees. Fake it by letting it see a library that will never be needed.
if python_library and not os.path.exists(python_library):
  python_libdir = os.path.join(install_dir, 'fake_python/lib')
  os.makedirs(python_libdir, exist_ok=True)
  python_library = os.path.join(python_libdir,
                                sysconfig.get_config_var('LIBRARY'))
  with open(python_library, 'wb') as f:
    pass

if python_library:
  cmake_args.append(f'-DPython3_LIBRARY:PATH={python_library}')

### Only enable shared library build on non-windows.
### TODO: Break this out into a separate dev package.
if not is_windows and False:
  cmake_args.append('-DLLVM_BUILD_LLVM_DYLIB=ON')
  # Enable development mode targets.
  cmake_targets.extend([
    # Headers.
    'install-llvm-headers',
    'install-mlir-headers',
    # CMake exports.
    'install-cmake-exports',
    'install-mlir-cmake-exports',
    # Shared libs.
    f'install-MLIR{stripped}',
    f'install-LLVM{stripped}',
    # Tools needed to build.
    f'install-mlir-tblgen{stripped}',
  ])

### Detect generator.
if use_tool_path('ninja'):
  report('Using ninja')
  cmake_args.append('-GNinja')
elif is_windows:
  cmake_args.extend(['-G', 'NMake Makefiles'])

# Detect other build tools.
use_ccache = use_tool_path('ccache')
if use_ccache:
  report(f'Using ccache {use_ccache}')
  cmake_args.append(f'-DCMAKE_CXX_COMPILER_LAUNCHER={use_ccache}')
use_lld = use_tool_path('lld')
if not is_windows and use_lld:
  report(f'Using linker {use_lld}')
  cmake_args.append('-DLLVM_USE_LINKER=lld')

report(f'Running cmake (generate): {" ".join(cmake_args)}')
subprocess.check_call(['cmake'] + cmake_args)
if CMAKE_ONLY:
  sys.exit(0)

cmake_build_args = [
    'cmake',
    '--build',
    build_dir,
    '--target',
] + cmake_targets
report(f'Running cmake (build/install): {" ".join(cmake_build_args)}')
subprocess.check_call(cmake_build_args)

### Hand-off to setuptools.
# Parse the command line and check the arguments
# before we proceed with building deps and setup
dist = Distribution()
dist.script_name = sys.argv[0]
dist.script_args = sys.argv[1:]
try:
  ok = dist.parse_command_line()
except DistutilsArgError as msg:
  raise SystemExit(core.gen_usage(dist.script_name) + "\nerror: %s" % msg)
if not ok:
  report('Finished running cmake configure and configured to exit.')
  report(f'You can continue manually in the build dir: {build_dir}')
  sys.exit()

# We do something tricky here with the directory layouts, synthesizing a
# top-level |mlir| package for the pure-python parts from $install_dir/python.
# Then we synthesize a "package" out of the install directory itself,
# including it as a |_mlir_libs| top-level package that then contains the
# native extensions under |_mlir_libs.python|, just like they are laid out
# on disk by the build system. This has the nice side-effect of letting us
# basically just emit the LLVM install dir as a python package and have
# everything work. The upstream |mlir| __init__.py is smart enough to
# see if it is in such an arrangement and change its behavior for such an
# out of tree distribution.
# We then put an __init__.py in the top-level install directory with a little
# API to query for build info and load extensions.

package_dir = os.path.join(install_dir, 'python')
packages = find_packages(where=package_dir)
report('Found packages:', packages)

header_files = [
    str(p.relative_to(install_dir))
    for p in pathlib.Path(install_dir).glob('include/mlir-c/**/*')
]

MLIR_LIB_INIT = f'''
import importlib
import os
import platform

SUFFIX = "{version_info.get('package-suffix') or ''}"
VERSION = "{version_info.get('package-version') or '0.1a1'}"
LLVM_COMMIT = "{version_info.get('llvm-revision') or 'UNKNOWN'}"

_is_windows = platform.system() == "Windows"
_this_directory = os.path.dirname(__file__)

def get_install_dir():
  """Gets the install directory of the LLVM tree."""
  return os.path.dirname(__file__)

def get_include_dir():
  """Gets the directory for include files."""
  return os.path.join(get_install_dir(), "include")

def get_lib_dir():
  """Gets the directory for include files."""
  return os.path.join(get_install_dir(), "lib")

def load_extension(name):
  """Loads a native extension bundled with these libraries."""
  return importlib.import_module("_mlir_libs.python." + name)

# The standard LLVM distribution tree for Windows is laid out as:
#   __init__.py (this file)
#   bin/
#     MLIRPublicAPI.dll
#   python/
#     _mlir.*.pyd (dll extension)
# First check the bin/ directory level for DLLs co-located with the pyd
# file, and then fall back to searching the python/ directory.
_dll_search_path = [
  os.path.join(_this_directory, "bin"),
  os.path.join(_this_directory, "python"),
]

# Stash loaded DLLs to keep them alive.
_loaded_dlls = []

def preload_dependency(public_name):
  """Preloads a dylib by its soname or DLL name.

  On Windows and Linux, doing this prior to loading a dependency will populate
  the library in the flat namespace so that a subsequent library that depend
  on it will resolve to this preloaded version.

  On OSX, resolution is completely path based so this facility no-ops. On
  Linux, as long as RPATHs are setup properly, resolution is path based but
  this facility can still act as an escape hatch for relocatable distributions.
  """
  if _is_windows:
    _preload_dependency_windows(public_name)


def _preload_dependency_windows(public_name):
  dll_basename = public_name + ".dll"
  found_path = None
  for search_dir in _dll_search_path:
    candidate_path = os.path.join(search_dir, dll_basename)
    if os.path.exists(candidate_path):
      found_path = candidate_path
      break

  if found_path is None:
    raise RuntimeError(
      "Unable to find dependency DLL %s in search "
      "path %r" % (dll_basename, _dll_search_path))

  import ctypes
  _loaded_dlls.append(ctypes.CDLL(found_path))

'''

# Turn the install directory into a valid package.
with open(os.path.join(install_dir, '__init__.py'), 'wt') as init_file:
  init_file.write(MLIR_LIB_INIT)
with open(os.path.join(install_dir, 'python', '__init__.py'),
          'wt') as init_file:
  pass

setup(
    name=f'mlir{version_info.get("package-suffix") or ""}',
    version=version_info.get("package-version") or "0.1a1",
    packages=packages + [
        '_mlir_libs',
        '_mlir_libs.python',
    ],
    package_dir={
        'mlir': os.path.join(install_dir, 'python', 'mlir'),
        '_mlir_libs': os.path.join(install_dir),
    },
    ext_modules=[
        # Note that this matches the build/install directory structure,
        # which makes rpath work properly.
        Extension(name="_mlir_libs.python._mlir", sources=[]),
        Extension(name="_mlir_libs.python._mlirTransforms", sources=[]),
    ],
    package_data={
        '_mlir_libs': [
            # By including the build extensions as package data, it keeps
            # the setuptools auto-builder from "compiling" them into a
            # static binary.
            f'python/*{sysconfig.get_config_var("EXT_SUFFIX")}',

            # Windows DLLs go in the bin dir and are otherwise not linked.
            # Import libs go in the lib dir.
            'bin/*.dll',
            'lib/*.lib',
            # Note that wild-carding all *.so duplicates all of the symlinks,
            # so we list one by one just the public names.
            'lib/libMLIRPublicAPI.so',
            'lib/libMLIRPublicAPI.dylib',

            # Cmake files.
            'lib/cmake/llvm/*.cmake',
            'lib/cmake/mlir/*.cmake',

            # Build tools.
            'bin/mlir-tblgen*',
        ] + header_files,
    },
    description='MLIR Python API',
    long_description=open(
        os.path.join(llvm_repo_dir, 'mlir', 'docs', 'Bindings', 'Python.md'),
        'r').read(),
    long_description_content_type="text/markdown",
    keywords="llvm, mlir",
    classifiers=[
        "Intended Audience :: Developers", "License :: OSI Approved :: "
        "Apache-2.0 WITH LLVM-exception", "Natural Language :: English",
        "Programming Language :: C", "Programming Language :: C++",
        "Programming Language :: Python",
        "Programming Language :: Python :: Implementation :: CPython"
    ],
    license='Apache-2.0 WITH LLVM-exception',
    zip_safe=False)
