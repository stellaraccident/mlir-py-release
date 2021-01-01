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
>>> _mlir_libs.get_lib_dir()
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

## Design methodology

The binary distribution is taking the approach of building minimal packages
with the API granularity that we intend to make public. This means that some
things are not available yet, usually because their underlying public APIs
are still in progress (or not started). It is much more effective to only
add things that you intend to support vs adding everything in a haphazzard
way and never be able to trim it down again.

As an example, a static, visibility hidden build of `libMLIRPublicAPI.so`
comes in at 6MiB on manylinux2014 (and the entire python wheel compresses down
to ~2.5MiB). To contrast this, a dynamic build of `libMLIR.so` is roughly 4x
that size, and `libLLVM.so` even more-so (by multiples). Included in the
smaller library are all core dialects, the public C-API, public C-API headers,
and core transformations. For things that *only* need this, the size is fairly
compelling.

There is definitely work to layer the other features that are useful, such
as JIT-ing, execution engines, LLVM code generation, etc, but these are
solvable technical problems that should only add cost to the people who
need them. By starting small and adding, we should be able to get to a
reasonable place and acrete good API boundaries in the process. This may mean
that some integrations need to wait, but that is fine.

It should also be noted that while a lot of people come to MLIR as a gateway
to LLVM code generation, it is useful for much more than that. As an example,
a full, linear algebra compilation system to SPIR-V based GPUs *only* needs
roughly the features in the above core API. Ditto for systems like IREE when
not targeting CPUs via LLVM.
