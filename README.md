# MLIR Python Release Scripts

This repository contains setup and packaging scripts for MLIR related
projects that need to build together. They may eventually go to their
respective homes, but developing them together for now helps.

## Prep

This repository is meant to be checked out adjacent to source repositories:

* `../llvm-project` : https://github.com/llvm/llvm-project.git
* `../mlir-npcomp` : https://github.com/llvm/mlir-npcomp.git

### Create a virtual environment:

Not strictly necessary, and if you know what you are doing, do that. Otherwise:

```shell
python -m venv create ~/.venv/mlir
source ~/.venv/mlir/bin/activate
```

### Install common dependencies:

```shell
python -m pip -r requirements.txt
```

NOTE: Some older distributions still have `python` as python 2. Make sure you
are running python3, which on these systems is often `python3`.

## Install into current python environment

If you are just looking to get packages that you can import and use, do:

```shell
python ./setup_mlir.py install
```

## Build wheel files (installable archives)

```shell
python ./setup_mlir.py bdist_wheel
```
