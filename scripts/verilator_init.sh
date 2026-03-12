set -euo pipefail

#verilator_init.sh

apt-get update
apt-get install -y \
    git\
    help2man\
    perl\
    make\
    autoconf\
    g++\
    flex\
    bison\
    ccache\
    libgoogle-perftools-dev\
    numactl\
    perl-doc #\
    # libfl2 \  # Ubuntu only (ignore if gives error)
    # libfl-dev \  # Ubuntu only (ignore if gives error)
    # zlibc \
    # zlib1g\
    # zlib1g-dev  # Ubuntu only (ignore if gives error)

mkdir LIBS
cd LIBS
git clone https://github.com/verilator/verilator   # Only first time

# Every time you need to build:
unset VERILATOR_ROOT  # For bash
cd verilator
git pull         # Make sure git repository is up-to-date
git tag          # See what versions exist

git checkout v5.036  # Switch to specified release version

autoconf         # Create ./configure script
./configure      # Configure and create Makefile
make -j `nproc`  # Build Verilator itself (if error, try just 'make')
make install

export VERILATOR_ROOT=/usr/local/share/verilator

cd --