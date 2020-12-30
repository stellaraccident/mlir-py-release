#  Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.
#  See https://llvm.org/LICENSE.txt for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

# Usage:
#   checkout_repo.py path repo_url branch version_file

import os
import subprocess
import sys

repo_path, repo_url, branch, version_file = sys.argv[1:]

with open(version_file, "rt") as f:
  revision = f.read().strip()

print(f"Checkout out repo {repo_path} from {repo_url} at revision {revision}")

os.makedirs(repo_path)


def run(*args, cwd=repo_path):
  print(f"Run: {' '.join(args)}  [from {cwd}]")
  subprocess.check_call(args, cwd=cwd)


run("git", "init")
run("git", "remote", "add", "origin", repo_url)
run("git", "config", "--local", "gc.auto", "0")
run("git", "-c", "protocol.version=2", "fetch", "--no-tags", "--prune",
    "--progress", "--no-recurse-submodules", "--depth=1", "origin",
    f"+{revision}:refs/remotes/origin/{branch}")
run("git", "checkout", "--progress", "--force", "-B", branch,
    "refs/remotes/origin/main")
run("git", "log", "-1", "--format='%H'")
