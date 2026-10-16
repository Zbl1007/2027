#!/usr/bin/env python3
"""Build the pinned existing solver on this macOS host; no automatic installs."""
import difflib
import json
import os
import platform
import shutil
import subprocess
import zipfile
from coupon_common import ROOT, digest, write_json

SRC = ROOT / "external/3d-ice"
LOCK = ROOT / "sources/three_d_ice.lock.json"
EVIDENCE = ROOT / "verification/three_d_ice_build"


def main():
    lock = json.loads(LOCK.read_text())
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    if not SRC.exists():
        SRC.parent.mkdir(exist_ok=True)
        subprocess.run(["git", "clone", lock["repository"], str(SRC)], check=True)
        subprocess.run(["git", "checkout", "--detach", lock["commit"]], cwd=SRC, check=True)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=SRC, text=True).strip()
    if head != lock["commit"]:
        raise ValueError("Checkout differs from locked commit")
    for name, sha in lock["files"].items():
        if digest(SRC/name) != sha:
            raise ValueError("Locked source changed: " + name)
    # Only the text exporter is patched: keep all thermal equations untouched.
    name = "sources/stack_element.c"
    original = subprocess.check_output(["git", "show", "HEAD:"+name], cwd=SRC, text=True)
    revised = original.replace('"%7.3f\\n", *(temperatures+counter)', '"%.17g\\n", *(temperatures+counter)')
    revised = revised.replace('SCALARS Temperature float 1', 'SCALARS Temperature double 1')
    assert revised != original
    if (SRC/name).read_text() not in (original, revised):
        raise ValueError("Unexpected local exporter modifications")
    patch = "".join(difflib.unified_diff(original.splitlines(True), revised.splitlines(True), fromfile="a/"+name, tofile="b/"+name))
    (ROOT/"patches").mkdir(exist_ok=True)
    (ROOT/"patches/3dice-vtk-precision.patch").write_text(patch)
    (SRC/name).write_text(revised)
    slu = SRC/"superlu_mt-4.0.0"
    if not slu.exists():
        with zipfile.ZipFile(SRC/"superlu_mt-4.0.0.zip") as archive:
            for entry in archive.namelist():
                if not (SRC/entry).resolve().is_relative_to(SRC.resolve()):
                    raise ValueError("Unsafe archive entry")
            archive.extractall(SRC)
    cc = os.environ.get("COUPON_CC", "/usr/bin/clang")
    blas = os.environ.get("COUPON_OPENBLAS", "/opt/homebrew/opt/openblas")
    omp = os.environ.get("COUPON_LIBOMP", "/opt/homebrew/opt/libomp")
    if not Path_exists(cc) or not Path_exists(blas):
        raise ValueError("Install Clang/libomp/OpenBLAS first, or set COUPON_* paths")
    ompflags = f"-Xpreprocessor -fopenmp -I{omp}/include"
    omplibs = f"-L{omp}/lib -lomp"
    inc = f"""PLAT = _OPENMP
SUPERLULIB = libsuperlu_mt$(PLAT).a
BLASDEF = -DUSE_VENDOR_BLAS
BLASLIB = -L{blas}/lib -lopenblas
MATHLIB = -lm
MPLIB =
ARCH = ar
ARCHFLAGS = cr
RANLIB = ranlib
PREDEFS = -D__OPENMP
CC = {cc} {ompflags}
CFLAGS = -std=gnu11 -O2 -fcommon -Wno-error=implicit-function-declaration $(PREDEFS) -DPRNTlevel=0 -DDEBUGlevel=0
NOOPTS = -O0
FORTRAN = /opt/homebrew/bin/gfortran-16 -fopenmp
FFLAGS = -O2
LOADER = {cc} {omplibs}
CDEFS = -DAdd_
"""
    (slu/"make.inc").write_text(inc)
    (slu/"lib").mkdir(exist_ok=True)
    commands = [
        ["make", "-C", str(slu/"SRC"), "double", "-j4"],
        ["make", "all", "CC="+cc, "YACC=/opt/homebrew/opt/bison/bin/bison", f"CFLAGS=-MD -std=gnu11 -O2 {ompflags} -fcommon -Wno-error=implicit-function-declaration -I{blas}/include",
         f"SLU_LIBS=-L{slu}/lib -lsuperlu_mt_OPENMP -L{blas}/lib -lopenblas {omplibs}"],
    ]
    with (EVIDENCE/"build.log").open("w") as log:
        for command in commands:
            log.write(repr(command)+"\n"); log.flush()
            subprocess.run(command, cwd=SRC, stdout=log, stderr=subprocess.STDOUT, check=True)
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=SRC).decode().split("\0")
    inputs = {p:digest(SRC/p) for p in tracked if p and (SRC/p).is_file()}
    binary = SRC/"bin/3D-ICE-Emulator"
    write_json(EVIDENCE/"build.json", {"status":"built", "commit":head, "platform":platform.platform(),
        "compiler":subprocess.check_output([cc,"--version"],text=True).splitlines()[0],
        "commands":commands, "working_tree_tracked_file_sha256":inputs,
        "export_patch_sha256":digest(ROOT/"patches/3dice-vtk-precision.patch"),
        "superlu_make_inc":inc, "superlu_archive_sha256":digest(SRC/"superlu_mt-4.0.0.zip"),
        "binary":str(binary.relative_to(ROOT)), "binary_sha256":digest(binary),
        "linked_libraries":subprocess.check_output(["otool","-L",str(binary)],text=True),
        "log_sha256":digest(EVIDENCE/"build.log")})
    print("Built pinned 3D-ICE; evidence: " + str(EVIDENCE))


def Path_exists(value):
    from pathlib import Path
    return Path(value).exists()


if __name__ == "__main__":
    main()
