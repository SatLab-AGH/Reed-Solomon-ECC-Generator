# Reed-Solomon-Generator

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE.md)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Project Status](https://img.shields.io/badge/Status-Active%20Development-brightgreen.svg)](CHANGELOG.md)
[![Encoder Status](https://img.shields.io/badge/Encoder-Production%20Ready-darkgreen.svg)](#project-status)
[![Decoder Status](https://img.shields.io/badge/Decoder-In%20Progress-orange.svg)](#project-status)
[![Planned Release](https://img.shields.io/badge/v1.0.0-06.2026-blue.svg)](CHANGELOG.md)

*A comprehensive Reed-Solomon Error-Correction Code (ECC) hardware generator for FPGA/ASIC designs—producing optimized, synthesizable Verilog from high-level specifications.*

> **Project Status:** This generator provides hardware generation for complete RS ECC operations. **Encoder is production-ready**, **Decoder is in active development** (target v1.0.0: June 2026). Currently verified through simulation only.

---

## Table of Contents

1. [Overview & Key Features](#overview--key-features)
2. [Project Status](#project-status)
3. [Architecture & Design](#architecture--design)
4. [Prerequisites & Requirements](#prerequisites--requirements)
5. [Installation & Setup](#installation--setup)
6. [Quick Start & Usage Examples](#quick-start--usage-examples)
7. [Configuration Reference](#configuration-reference)
8. [Hardware Generation Pipeline](#hardware-generation-pipeline)
9. [Testing & Verification](#testing--verification)
10. [Hardware Integration Guide](#hardware-integration-guide)
11. [Project Structure](#project-structure)
12. [Contributing](#contributing)
13. [Troubleshooting](#troubleshooting)
14. [Known Limitations & Future Work](#known-limitations--future-work)
15. [Security & Scope](#security--scope)
16. [License & Acknowledgements](#license--acknowledgements)

---

## Overview & Key Features

The **Reed-Solomon-Generator** is a Python-based hardware design automation (HDA) toolchain for generating optimized Reed-Solomon error-correction IP blocks in Verilog. It implements the **Mastrovito multiplication algorithm**—a parallel, XOR-based Galois Field multiplier—to accelerate RS encoding/decoding operations in hardware.

### Core Features

* **Customizable RS Parameters:** 
  - Word sizes: 1–12 bits
  - Parity symbols: 1–511
  - Custom irreducible polynomials for GF(2^m) fields
  
* **Mastrovito Acceleration:** Implements parallel XOR-based multipliers for constant-time Galois Field multiplication (single-cycle latency)

* **Complete RS Pipeline:** 
  - ✅ **Encoder (Production-Ready):** Fully functional Reed-Solomon encoder with comprehensive simulation coverage
  - 🔄 **Decoder (In Development):** Complete RS decoding pipeline (ETA: v1.0.0, June 2026)
  
* **AXI-Stream Integration:** Generated modules wrap seamlessly in AXI-Stream interfaces for plug-and-play FPGA integration

* **Comprehensive Testing:** Cocotb-based simulation suite with cross-validation against reference implementations (reedsolo)

* **DevContainer Support:** Fully containerized development environment with all tools pre-configured

### Use Cases

* Satellite communication systems (PUCHACZ mission, DZIDA laser link)
* Deep-space data downlinks
* High-reliability storage systems
* Wireless broadband systems requiring FEC
* Any ASIC/FPGA-based system requiring RS ECC

---

## Project Status

| Component | Status | Target |
|-----------|--------|--------|
| **RS Encoder** | ✅ Production-Ready | — |
| **RS Decoder** | 🔄 In Development | v1.0.0 (06.2026) |
| **Hardware Verification** | 📋 Simulation-Only | Post-FPGA-Prototyping |
| **Performance Metrics** | 📋 TODO | v1.0.0 |
| **Code Coverage** | 📋 TODO | v1.0.0 |

**Maintenance:** Active development as of March 2026. Updated regularly via the [SatLab AGH](https://satlab.agh.edu.pl/) internal repository, mirrored to GitHub.

---

## Architecture & Design

### System Overview

The Reed-Solomon-Generator follows a hierarchical hardware generation pipeline:

```
┌─────────────────────────────────────────────────────────────┐
│  High-Level Specification (Python Parameters)              │
│  • WORD_SIZE, ECC_LEN, IRR_GF_POLY                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Mastrovito Matrix Computation                              │
│  • GF(2^m) irreducibility validation                        │
│  • Parallel XOR multiplier synthesis                        │
│  (MastrovitoMatrix.py → MastrovitoVerilog.py)              │
└────────────────────┬────────────────────────────────────────┘
                     │
       ┌─────────────┼─────────────┐
       │             │             │
       ▼             ▼             ▼
┌──────────────┐ ┌──────────┐ ┌─────────────┐
│ RS_Segment   │ │Mastrovito│ │Verilog      │
│ Multiplier   │ │ Verilog  │ │ Templates   │
│ Generator    │ │Generator │ │ Engine      │
└──────┬───────┘ └──────────┘ └─────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│  RS_Segment Module (Per-segment GF Multiplier-Adder)       │
│  • Implements A*B+C operation in GF(2^m)                   │
│  • Backward bypass path for RS pipeline                     │
│  • One-cycle latency                                        │
│  Parameterizable: GF_CONST_MULT                             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  RS_Accumulator Module (Core Encoder Logic)                 │
│  • Chains N RS_Segment instances                            │
│  • Implements RS generator polynomial                       │
│  • Parity symbol generation & feedback control             │
│  Dependencies: RSSegmentVerilog                             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  RS_AXIS Module (AXI-Stream Wrapper)                        │
│  • AXI-Stream slave/master interfaces                       │
│  • Automatic parity append on TLAST                         │
│  • Feedback control for proper accumulation                │
│  Dependencies: RSAccumulatorVerilog                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
            ┌────────────────────┐
            │ Synthesizable      │
            │ Verilog Output:    │
            │ • RS_Segment.v     │
            │ • RS_Accumulator.v │
            │ • RS_AXIS.v        │
            └────────────────────┘
```

### Module Hierarchy

| Module | Source File | Purpose | Key Interfaces |
|--------|-------------|---------|-----------------|
| **RS_Segment** | `RSSegmentVerilog.py` | GF(2^m) multiplier-adder (A*B+C) using Mastrovito XOR matrix with constant A. Provides backward bypass for pipeline architecture with one-cycle latency. | `clk`, `rst_n`, `RS_Backward_I/O`, `RS_Forward_I/O` |
| **RS_Accumulator** | `RSAccumulatorVerilog.py` | Chains RS_Segment instances to form complete RS encoder. Implements generator polynomial coefficients for parity calculation and feedback paths. | `clk`, `rst_n`, `acc_input`, `acc_output`, `feedback` |
| **RS_AXIS** | `RSAXISVerilog.py` | Wraps RS_Accumulator with AXI-Stream interface for protocol-compliant FPGA integration. Handles automatic parity symbol append on frame end (TLAST signal). | `aclk`, `areset_n`, `axis_s_*` (slave input), `axis_m_*` (master output) |

### Architecture Diagram (Detailed)
Reference: [Reed-Solomon](https://www.iiis.org/cds2010/cd2010imc/ccct_2010/paperspdf/ta999ne.pdf)

[**Architecture Diagram Placeholder**](docs/architecture.drawio)

*For visual architecture details, see the drawio diagram file (to be filled with detailed signal flows, memory mappings, and pipeline diagrams).*

### Key Design Concepts

#### Mastrovito Matrix Algorithm

The **Mastrovito algorithm** replaces iterative GF multiplication with a **parallel, combinational XOR circuit** based on matrix multiplication in GF(2). For each constant multiplicand A and variable input B:

```
C = Mastrovito(A) × B  (in GF(2^m))
```

**Key Benefit:** Single-cycle combinational logic with zero iteration overhead, enabling high-throughput pipelined architectures.

**Mathematical Basis:**
- Reference: [Mastrovito Multiplier](https://cetinkayakoc.net/docs/c18.pdf)
- Implementation: XOR gates arranged in parallel to compute all output bits simultaneously

#### Backward Bypass Path

RS encoders require feedback of intermediate state through the accumulator. The RS_Segment backward path enables this without requiring additional XOR gates—data can flow "backward" through the pipeline with zero additional latency. This is critical for:
- Parity symbol generation
- Proper state sequencing in the accumulator chain
- Minimal critical path delay

#### Irreducible Polynomial

Every Galois Field GF(2^m) is defined by an **irreducible polynomial P(x)** of degree m over GF(2). The generator selects or validates your provided polynomial to ensure proper field construction.

**Common Examples:**
- **GF(2^8):** P(x) = x⁸ + x⁴ + x³ + x² + 1 (AES standard, 0x11D)
- **GF(2^10):** P(x) = x¹⁰ + x³ + 1 (0x409)
- **GF(2^16):** P(x) = x¹⁶ + x¹² + x³ + x + 1 (0x1002B)

Auto-selection uses the `galois` library to find valid polynomials if not provided.

---

## Prerequisites & Requirements

### System Requirements

* **OS:** Linux (Ubuntu 22.04+) or any with Docker
* **Docker:** For DevContainer support (recommended)
* **Disk Space:** ~4 GB for dependencies and build artifacts

### Python Environment

* **Python:** 3.12+ (strictly required)
* **Package Manager:** `uv` (ultra-fast, Astral Python package manager—auto-installed in DevContainer)

### HDL Simulation & Verification (Required for Testing)

* **Icarus Verilog:** v10.3+ (CPU-based simulator, included in Dockerfile)
* **Verilator:** v5.0+ (optional, C++-based simulator for faster elaboration for long tests (mind compile times); installed via `scripts/verilator_init.sh`)
* **Cocotb:** v2.0.1+ (Co-simulation framework, auto-installed)

### Optional Tools

* **GTKWave:** Waveform viewer for debugging (included in Dockerfile)
* **Graphviz:** For architecture diagrams (included in Dockerfile)
* **Yosys:** FPGA synthesis tool (included in Dockerfile)

---

## Installation & Setup

### Option 1: DevContainer (Recommended)

**Prerequisites:** VSCode with Remote-Containers extension installed

1. **Clone the repository**

   ```bash
   git clone git@github.com:SatLab-AGH/Reed-Solomon-ECC-Generator.git
   cd reed-solomon-generator
   ```

2. **Open in DevContainer**

   Open the folder in VSCode. The editor will detect `.devcontainer/devcontainer.json` and prompt to reopen in container. Click **"Reopen in Container"**.

   Alternatively, use the Command Palette (`Ctrl+Shift+P`) and select "Dev Containers: Reopen in Container".

3. **Python Env Initialization**
   ```bash
    uv sync --active
   ```

3. **Verify Installation**

   Inside the container:
   ```bash
   python3 --version          # Should be 3.12+
   uv --version               # Should be ≥ 0.15.0
   iverilog -v                # Verify Verilog simulator
   ```

---

## Quick Start & Usage Examples

### Basic Usage: Generate RS Encoder (10-bit symbols, 16 parity symbols)

```bash
python3 src/main.py --WORD_SIZE 10 --ECC_LEN 16 --OUTPUT_DIR ./output
```

**Output Files:**
- `output/RS_Segment.v` — Galois Field multiplier-adder module
- `output/RS_Accumulator.v` — Encoder core module
- `output/RS_AXIS.v` — AXI-Stream wrapper

### Run Tests

```bash
./scripts/mcore_regr.sh
```

This runs the complete test suite with parametrized ECC lengths (1–255 symbols) using Icarus Verilog and Cocotb.

### Sanity Check (Fast Module Generation)

```bash
./scripts/sanity.sh
```

Generates all module types once to verify the toolchain is functional.

---

## Configuration Reference

### Command-Line Parameters

All parameters can be provided via CLI arguments or a JSON configuration file.

#### CLI Arguments

```bash
python src/main.py \
  --WORD_SIZE <1-15> \
  --ECC_LEN <1-511> \
  --IRR_GF_POLY <int> \
  --OUTPUT_DIR <path>
```

| Parameter | Type | Range | Default | Description |
|-----------|------|-------|---------|-------------|
| `--WORD_SIZE` | int | 1–15 | 8 | Symbol width in bits (GF field degree m). Defines field size 2^m. |
| `--ECC_LEN` | int | 1–511 | 8 | Number of parity symbols to append (n_sym in RS(n, k)). |
| `--IRR_GF_POLY` | int | — | Auto | Integer representation of irreducible polynomial (e.g., 0x11D for GF(2^8)). If omitted, auto-selects. |
| `--OUTPUT_DIR` | path | — | `./products` | Destination directory for generated Verilog files. |

#### Constraints

* **WORD_SIZE range:** 1 ≤ WORD_SIZE < 16
* **ECC_LEN range:** 1 ≤ ECC_LEN ≤ 511
* **Irreducible Polynomial:** Must satisfy Galois Field irreducibility requirements (validated by `galois` library)

### Configuration File (JSON)

Alternative to CLI arguments: pass a JSON config file.

**Example: `config.json`**

```json
{
  "company": "SatLab AGH",
  "engineer": "Your Name",
  "project_name": "PUCHACZ-ECC",
  "word_size": 10,
  "ecc_len": 16,
  "irr_gf_poly": 1033,
  "output_dir": "./output"
}
```

**Usage:**

```bash
python src/main.py --CONFIG config.json
```

**Config File Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `company` | string | ✓ | Company/organization name (added to Verilog headers) |
| `engineer` | string | ✓ | Engineer name (added to Verilog headers) |
| `project_name` | string | ✓ | Project identifier (added to Verilog headers) |
| `word_size` | int | ✓ | Symbol width (1–15) |
| `ecc_len` | int | ✓ | Number of parity symbols (1–511) |
| `irr_gf_poly` | int | ✓ | Irreducible polynomial (integer form) |
| `output_dir` | path | ✓ | Output directory for generated files |

### Environment Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `SIM` | string | `icarus` | Simulator backend for tests: `icarus` or `verilator` |
| `WAVES` | bool | 0 | Assert this to generate waveform for manual inspection |

---

## Hardware Generation Pipeline

### Step 1: Mastrovito Matrix Computation

```python
MastrovitoMatrix.py
├── Input: word_size, irreducible_poly_coeffs
├── Validate GF(2^m) irreducibility
└── Output: Parallel XOR multiplier matrix
```

### Step 2: Verilog Module Generation

```
RSSegmentVerilog.py
├── Input: Mastrovito matrix, constant multipliers
├── Generate GF(2^m) multiplier functions
└── Output: RS_Segment.v

RSAccumulatorVerilog.py
├── Input: RS_Segment modules, generator polynomial
├── Chain segments + feedback paths
└── Output: RS_Accumulator.v

RSAXISVerilog.py
├── Input: RS_Accumulator
├── Wrap with AXI-Stream interface
└── Output: RS_AXIS.v
```

### Step 3: Integration & Simulation

Generated modules are synthesizable and can be:
- **Simulated** with Icarus Verilog / Verilator + Cocotb
- **Synthesized** with Yosys / Vivado / Quartus
- **Integrated** into larger designs via AXI-Stream bus

---

## Testing & Verification

### Test Categories

#### 1. **Unit Tests** (Fast, ~5 seconds)

Test individual mathematical components:

```bash
cd src && uv run python3 -m generators.MastrovitoMatrix
uv run python3 -m generators.RSSegmentVerilog
uv run python3 -m generators.RSAccumulatorVerilog
```

**Coverage:**
- Mastrovito matrix correctness (against galois reference)
- GF polynomial irreducibility validation

#### 2. **Simulation Tests** (Cocotb-based, ~3 minutes)

Full integration tests with HDL simulation:

```bash
pytest tests/TestRSAXISVerilog.py -v
```

**Coverage:**
- RS encoder correctness (against reedsolo reference)
- AXI-Stream protocol compliance
- Parity symbol generation for various ECC lengths (1–255)
- Random data payloads and frame sizes

**Parameters Tested:**
- `ECC_LEN`: 1–255 (2^i - 1 for i ∈ [1, 8])
- `WORD_SIZE`: Fixed at 10 bits (configurable)
- `GF_PRIM`: Irreducible polynomial validation

#### 3. **Regression Suite** (Full, ~10 min)

Complete multi-threaded test execution:

```bash
./scripts/mcore_regr.sh
```

Runs with `pytest -n 4` for parallel execution on 4 cores.

### Test Coverage Status

| Component | Coverage | Status |
|-----------|----------|--------|
| Mastrovito Matrix | Core functions | ✓ Tested |
| GF Arithmetic | XOR operations | ✓ Tested |
| RS Encoder | Full pipeline | ✓ Tested |
| AXI-Stream Protocol | Master/Slave | ✓ Tested |
| Decoder Pipeline | — | 📋 TODO (v1.0) |
| Code Coverage (%) | — | 📋 TODO (v1.0) |

### Running Tests with Different Simulators

```bash
SIM=icarus pytest tests/ -v
SIM=verilator pytest tests/ -v
```

## Hardware Integration Guide

### Generated Module Interfaces
#### RS_AXIS Interface

```verilog
module RS_AXIS (
  // Clock & Reset
  input  aclk,
  input  areset_n,
  
  // AXI-Stream Slave (Input)
  input  axis_s_tvalid,
  output axis_s_tready,
  input  [WORD_SIZE-1:0] axis_s_tdata,
  input  axis_s_tlast,
  
  // AXI-Stream Master (Output)
  output axis_m_tvalid,
  input  axis_m_tready,
  output [WORD_SIZE-1:0] axis_m_tdata,
  output axis_m_tlast
);
```

**Protocol:** Standard AXI-Stream (AMBA 4)
- Handshake: `tvalid` & `tready`
- Frame markers: `tlast` (end-of-frame)
- Automatic parity append: Parity symbols appended after `tlast` assertion, new tlast is asserterd on last word of ECC
- Latency: 0 cycles (configurable)

### Integration Steps

1. **Generate Modules**

   ```bash
   python src/main.py --WORD_SIZE 10 --ECC_LEN 16 --OUTPUT_DIR ./ip
   ```

2. **Add to Project**

   Copy generated files to your FPGA project:
   ```bash
   cp ip/RS_*.v /path/to/project/ip/
   ```

3. **Instantiate RS_AXIS**

   In your top-level Verilog/VHDL:
   ```verilog
   RS_AXIS #(
     .WORD_SIZE(10),
     .N_PARITY(16)
   ) rs_encoder_inst (
     .aclk(clk),
     .areset_n(rst_n),
     .axis_s_tvalid(from_source_valid),
     .axis_s_tready(to_source_ready),
     .axis_s_tdata(from_source_data),
     .axis_s_tlast(from_source_last),
     .axis_m_tvalid(to_sink_valid),
     .axis_m_tready(from_sink_ready),
     .axis_m_tdata(to_sink_data),
     .axis_m_tlast(to_sink_last)
   );
   ```

4. **Connect AXI-Stream Sources/Sinks**

   Use standard AXI infrastructure libraries (e.g., `cocotbext-axi` for simulation, Xilinx IPI for synthesis).

5. **Synthesize & Place**

   Use your standard FPGA flow (Vivado, Quartus, etc.). No special constraints required.

### Performance Considerations

| Metric | Value | Notes |
|--------|-------|-------|
| **Throughput** | 1 symbol/cycle | Fixed latency pipeline |
| **Latency** | 0 cycles | Data-in to Data-out |
| **Clock Frequency** | TODO | v1.0 metrics |
| **Area (LUTs)** | TODO | v1.0 metrics |
| **Area (FFs)** | TODO | v1.0 metrics |
| **BRAM Usage** | 0 | No memory required |

---

## License & Acknowledgements  

This repository is shared via [MIT License](LICENSE.md).

This code is developed for [DZIDA](https://satlab.agh.edu.pl/puchacz.html) Laser Communication Project for a PUCHACZ Sattelite mission.

Jan Rosa is developer contributing to Reed-Solomon Encoder Module.

Mateusz Maź is developer contributing to Reed-Solomon Decoder Module.

> **Note:** Main work is done on [SatLab AGH](https://satlab.agh.edu.pl/) internal repository, any features and bugs will be worked on there and then merged to main mirrored to GitHub for the time project is developed for [SatLab AGH](https://satlab.agh.edu.pl/).

### Huge thanks people contributing to:
+ [reedsolo](https://github.com/tomerfiliba-org/reedsolomon)
+ [cocotb](https://github.com/cocotb/cocotb)
+ [cocotbext-axi](https://github.com/alexforencich/cocotbext-axi)
+ [verilator](https://github.com/verilator/verilator)
+ [Icarus Verilog](https://github.com/steveicarus/iverilog)
+ [galois](https://github.com/mhostetter/galois)

## Sources
 + [FPGA Implementation of a Reed-Solomon CODEC for OTN G.709 Standard with Reduced Decoder Area](https://www.iiis.org/cds2010/cd2010imc/ccct_2010/paperspdf/ta999ne.pdf)
 + [Mastrovito Multiplier for General Irreducible Polynomials](https://cetinkayakoc.net/docs/c18.pdf)
 + [Reed-Solomon Error Correcting Codes from the Bottom Up](https://tomverbeure.github.io/2022/08/07/Reed-Solomon.html)
 + [Implementation of Reed-Solomon Encoder/Decoder Using Field Programmable Gate Array](https://www.researchgate.net/publication/234778328_Design_and_implementation_of_Reed-Solomon_EncoderDecoder_usingFPGA/download?_tp=eyJjb250ZXh0Ijp7ImZpcnN0UGFnZSI6Il9kaXJlY3QiLCJwYWdlIjoiX2RpcmVjdCJ9fQ)
