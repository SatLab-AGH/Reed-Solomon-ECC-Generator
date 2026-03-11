# Reed-Solomon-Generator  

*Generate Reed-Solomon encoder/decoder hardware (Verilog) from high-level specifications.*

---  

## Table of Contents  

1. [Project Overview](#project-overview)  
2. [Prerequisites](#prerequisites)  
3. [Installation & Setup](#installation--setup)  
4. [Quick Start](#quick-start)  
5. [Generating Verilog](#generating-verilog)  
6. [Running the Test Suite](#running-the-test-suite)  
7. [Project Structure](#project-structure)  
8. [Contributing](#contributing)  
9. [License & Acknowledgements](#license--acknowledgements)  

---  

## Project Overview  

The **Reed-Solomon-Generator** repository provides a Python-based toolchain that:

* Takes Reed-Solomon parameters (field size, irreducible polynomial, parity length, etc.) and produces synthesizable Verilog modules.  
* Supports three main hardware blocks:  

| Block | Source file | Description |
|-------|-------------|-------------|
| **RS Segment Generator** | `src/generators/RSSegmentVerilog.py` | Generates the per-segment multiplier logic used by the accumulator. |
| **RS Accumulator** | `src/generators/RSAccumulatorVerilog.py` | Implements the core Reed-Solomon accumulator (parity calculation). |
| **RS AXI-Stream ECC Generator** | `src/generators/RSAXISVerilog.py` | Wraps the accumulator with an AXI-Stream front-end for easy integration in FPGA designs. |

The generated Verilog can be dropped into an any RTL project and connected to other IP blocks via the provided AXI-Stream interface.

---  

## Prerequisites

This project is developed in Devcontainer Docker environment other ways are probably possible but not supported.
Defined in [Dockerfile](Dockerfile) and in [PyProject.toml](pyproject.toml)

---  

## Installation & Setup  

1. **Clone the repository**  

   ```bash
   git clone git@github.com:SatLab-AGH/Reed-Solomon-ECC-Generator.git
   cd reed-solomon-generator
   ```

2. **Open the devcontainer**  

   If you use VSCode with Remote-Containers, the configuration lives in `.devcontainer/devcontainer.json`. Opening the folder in VSCode will automatically spin up a Docker container with all extensions listed (Python, C/C++, Verilog, Ruff, etc.).


3. **Sync Python environment with `uv`**  

   ```bash
   uv sync --active  # installs dependencies from pyproject.toml
   ```

4. **(For contributors) Install pre-commit**  

   ```bash
   pre-commit install
   ```

---  

## Quick Start  

Below is a minimal example command that generates a complete Verilog module for a Reed-Solomon encoder with 10-bit symbols and 16 parity symbols.

   ```bash
   /workspace/.venv/bin/python /workspace/src/main.py --WORD_SIZE 10 --ECC_LEN 16 --OUTPUT_DIR output 
   ```

---

## Generating Verilog  

The core generation flow is:

1. **Mastrovito matrix**  `MastrovitoMatrix` creates the multiplication matrix needed for GF(2^m) operations.  
1. **Segment multiplier**  `RSSegmentVerilog` uses the matrix and the list of constant multiplicants to emit per-segment Verilog.  
1. **Accumulator**  `RSAccumulatorVerilog` wires the segment modules together and adds the parity-generation logic.  
1. **AXI-Stream wrapper**  `RSAXISVerilog` adds the AXI-Stream interface and feedback control.

---  

## Running the Test Suite  

The repository ships with a pytest-compatible test suite under `tests/`.  

```bash
. ./scripts/mcore_regr.sh
```

---  

## Contributing  

1. **Fork** the repository and create a feature branch.  
2. **Run the pre-commit hooks** before committing:  

   ```bash
   pre-commit run --all-files
   ```

3. **Write tests** for any new functionality.  
4. **Submit a Merge Request** via GitHub.  

> **Note:** Main work is done on [SatLab AGH](https://satlab.agh.edu.pl/) internal repository, any features and bugs will be worked on there and then merged to main mirrored to GitHub for the time project is developed for [SatLab AGH](https://satlab.agh.edu.pl/).

---  

## License & Acknowledgements  

This repository is shared via [MIT License](LICENSE.md).

This code is developed for [DZIDA](https://satlab.agh.edu.pl/puchacz.html) Laser Communication Project for a PUCHACZ Sattelite mission.

Jan Rosa is developer contributing to Reed-Solomon Encoder Module.

Mateusz Maź is developer contributing to Reed-Solomon Decoder Module.

Huge thanks people contributing to:
+ [reedsolo](https://github.com/tomerfiliba-org/reedsolomon)
+ [cocotb](https://github.com/cocotb/cocotb)
+ [cocotbext-axi](https://github.com/alexforencich/cocotbext-axi)
+ [verilator](https://github.com/verilator/verilator)
+ [Icarus Verilog](https://github.com/steveicarus/iverilog)
---  