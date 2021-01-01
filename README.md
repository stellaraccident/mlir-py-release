# MLIR Python Release Scripts

This repository contains setup and packaging scripts for MLIR related
projects that need to build together. They may eventually go to their
respective homes, but developing them together for now helps.

[![Build MLIR Wheels](https://github.com/stellaraccident/mlir-py-release/workflows/Build%20MLIR%20Wheels/badge.svg)](https://github.com/stellaraccident/mlir-py-release/actions?query=workflow%3A%22Build+MLIR+Wheels%22+branch%3Amain)

[![GitHub release (latest by date including pre-releases)](https://img.shields.io/github/v/release/stellaraccident/mlir-py-release?include_prereleases)](https://github.com/stellaraccident/mlir-py-release/releases)


## Installation

Note that this is a prototype of a real MLIR release process being run by
a member of the community. These are not official releases of the LLVM
Foundation in any way, and they are likely only going to be useful to people
actually working on LLVM/MLIR until we get things productionized.

Links to more official places:

* Overall [LLVM page](https://llvm.org/)
* [MLIR main page](https://mlir.llvm.org/)
* [MLIR Channel within LLVM Discourse](https://llvm.discourse.group/c/mlir/31)
* [MLIR Python Bindings Doc](https://mlir.llvm.org/docs/Bindings/Python/)

We are currently only producing snapshot releases twice a day at llvm-project
head. Each time we bump the revision, we create a new "snapshot" release on
the [releases page](https://github.com/stellaraccident/mlir-py-release/releases).

You can use pip to install the latest for your platform directly from that
page (or use a link to a specific release). Note that tests have not yet been
integrated: these may not work at all.

```shell
python -m pip install --upgrade mlir-snapshot -f https://github.com/stellaraccident/mlir-py-release/releases
```

And verify some things:

```python
>>> import mlir
>>> help(mlir._cext.ir)  # TODO: Should be available under mlir.ir directly
>>> from mlir.dialects import std
>>> help(std)
```

Show version info:

```python
# TODO: These should come from the main mlir module.
>>> import _mlir_libs
>>> _mlir_libs.LLVM_COMMIT
'8d541a1fbe6d92a3fadf6d7d8e8209ed6c76e092'
>>> _mlir_libs.VERSION
'20201231.14'
>>> _mlir_libs.get_cmake_dir() # TODO: Not working
>>> _mlir_libs.get_lib_dir()   # TODO: Not working
>>> _mlir_libs.get_include_dir()
```

## Manually packaging releases

This is intended for people working on the release pipeline itself. If you
just want binaries, see above.

### Prep

This repository is meant to be checked out adjacent to source repositories:

* `../llvm-project` : https://github.com/llvm/llvm-project.git
* `../mlir-npcomp` : https://github.com/llvm/mlir-npcomp.git

#### Create a virtual environment:

Not strictly necessary, and if you know what you are doing, do that. Otherwise:

```shell
python -m venv create ~/.venv/mlir
source ~/.venv/mlir/bin/activate
```

#### Install common dependencies:

```shell
python -m pip -r requirements.txt
```

NOTE: Some older distributions still have `python` as python 2. Make sure you
are running python3, which on these systems is often `python3`.

### Install into current python environment

If you are just looking to get packages that you can import and use, do:

```shell
python ./setup_mlir.py install
```

### Build wheel files (installable archives)

```shell
python ./setup_mlir.py bdist_wheel
```
