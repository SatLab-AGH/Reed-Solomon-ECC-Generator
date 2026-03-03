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
| **RS Accumulator** | `src/generators/RSAccumulatorVerilog.py` | Implements the core Reed-Solomon accumulator (parity calculation). |
| **RS AXI-Stream ECC Generator** | `src/generators/RSAXISVerilog.py` | Wraps the accumulator with an AXI-Stream front-end for easy integration in FPGA designs. |
| **RS Segment Generator** | `src/generators/RSSegmentVerilog.py` | Generates the per-segment multiplier logic used by the accumulator. |

The generated Verilog can be dropped into an FPGA project and connected to other IP blocks via the provided AXI-Stream interface.

---  

## Prerequisites  

Defined in dockerfile

---  

## Installation & Setup  

1. **Clone the repository**  

   ```bash
   git clone https://gitlab.satlab.agh.edu.pl/satlab/fpga_payload/reed-solomon-generator.git
   cd reed-solomon-generator
   ```

2. **Create a Python environment with `uv`**  

   ```bash
   uv sync   # installs dependencies from pyproject.toml
   ```

3. **(Optional) Open the devcontainer**  

   If you use VS\UffffffffCode with Remote-Containers, the configuration lives in `.devcontainer/devcontainer.json`. Opening the folder in VS\UffffffffCode will automatically spin up a Docker container with all extensions listed (Python, C/C++, Verilog, Ruff, etc.).

---  

## Quick Start  

Below is a minimal example command that generates a complete Verilog module for a Reed-Solomon encoder with 10-bit symbols and 16 parity symbols.

/workspace/.venv/bin/python /workspace/src/main.py --WORD_SIZE 10 --ECC_LEN 16 --OUTPUT_DIR output 

## Generating Verilog  

The core generation flow is:

1. **Mastrovito matrix** \Uffffffff `MastrovitoMatrix` creates the multiplication matrix needed for GF(2^m) operations.  
1. **Segment multiplier** \Uffffffff `RSSegmentVerilog` uses the matrix and the list of constant multiplicants to emit per-segment Verilog.  
1. **Accumulator** \Uffffffff `RSAccumulatorVerilog` wires the segment modules together and adds the parity-generation logic.  
1. **AXI-Stream wrapper** \Uffffffff `RSAXISVerilog` adds the AXI-Stream interface and feedback control.

---  

## Running the Test Suite  

The repository ships with a pytest-compatible test suite under `tests/`.  

```bash
. ./scripts/mcore_regr.sh
```

Key test files:

| Test | What it validates |
|------|-------------------|
| `tests/TestMastrovito.py` | Correctness of the Mastrovito matrix generation. |
| `tests/TestMastrovitoVerilog.py` | Verilog output for the Mastrovito module. |
| `tests/TestRSAccumulatorVerilog.py` | ECC generation matches `reedsolo.RSCodec`. |
| `tests/TestRSAXISVerilog.py` | End-to-end AXI-Stream ECC verification. |
| `tests/TestRSSegmentVerilog.py` | Stimulus driver for the segment multiplier. |

> **Note:** The tests rely on the `reedsolo` Python package and a Verilog simulator (e.g., cocotb). Make sure those are installed and reachable from your environment.

---  

## Contributing  

1. **Fork** the repository and create a feature branch.  
2. **Run the pre-commit hooks** before committing:  

   ```bash
   pre-commit install
   pre-commit run --all-files
   ```

3. **Write tests** for any new functionality.  
4. **Submit a Merge Request** via GitLab.  

The CI pipeline defined in `.gitlab-ci.yml` will automatically lint (Ruff), type-check, and run the test suite on every push.

---  

## License & Acknowledgements  

*License information goes here (e.g., MIT, Apache-2.0, etc.).*  

*Acknowledgements for any third-party libraries (e.g., `reedsolo`, `cocotb`, `uv`, Ollama models) can be added here.*  

---  