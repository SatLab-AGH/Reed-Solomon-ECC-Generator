# MIT License

# Copyright (c) 2026 Jan Rosa, Mateusz Maź, SatLab AGH

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any

import galois

from generators.RSAXISVerilog import RSAXISVerilogGenerator, RSAXISVerilogParameters
from resources.YosysWrap import SynthTarget, YosysWrapper

logger = logging.getLogger(__name__)
proj_path = Path(__file__).resolve().parent.parent.parent


@dataclass
class ResourceReport:
    """Individual resource report for a single configuration"""

    config_name: str
    target: str
    success: bool
    num_wires: int = 0
    num_wire_bits: int = 0
    num_public_wires: int = 0
    num_public_wire_bits: int = 0
    num_memories: int = 0
    num_memory_bits: int = 0
    num_processes: int = 0
    num_cells: int = 0
    custom_cells: dict = field(default_factory=dict)  # e.g., {"LUT4": 189, "TRELLIS_FF": 166}
    num_lut: int = 0
    num_ff: int = 0
    num_bram: int = 0
    num_io: int = 0
    max_freq_mhz: float = 0.0
    error_message: str = ""
    yosys_log_path: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


class ConfigLoader:
    """Load and parse configuration from JSON file"""

    @staticmethod
    def load(config_path: str | Path) -> list[dict[str, Any]]:
        """
        Load configuration from JSON file.

        Args:
            config_path: Path to config.json

        Returns:
            List of configuration dictionaries
        """
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with Path.open(config_path) as f:
            configs = json.load(f)

        if not isinstance(configs, list):
            raise ValueError("Config file must contain a list of configuration objects")

        logger.info(f"Loaded {len(configs)} configurations from {config_path}")
        return configs


class GenerationManager:
    """Manage HDL generation using first configuration"""

    @staticmethod
    def generate_hdl(configs: list[dict], output_dir: str | Path | None = None) -> tuple[Path, Path, Path]:
        """
        Generate HDL files using the first configuration's parameters.

        Args:
            configs: List of configuration dictionaries
            output_dir: Output directory (default: build/rtl)

        Returns:
            Tuple of (segment_path, accumulator_path, axis_path)
        """
        if not configs:
            raise ValueError("No configurations provided")

        first_config = configs[0]
        output_dir = Path(output_dir) if output_dir else proj_path / "build" / "rtl" / "yosys"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Extract parameters from first config
        params = GenerationManager._build_verilog_params(first_config)

        logger.info(
            f"Generating HDL with parameters: word_size={params['word_size']}, "
            f"n_parity_sym={params['n_parity_sym']}"
        )

        # Generate Verilog files
        generator = RSAXISVerilogGenerator(params)
        segment_path = output_dir / "RS_Segment.v"
        acc_path = output_dir / "RS_Accumulator.v"
        axis_path = output_dir / "RS_AXIS.v"

        generator.generate_all_files(
            segment_path=str(segment_path.parent),
            acc_filepath=str(acc_path.parent),
            axis_filepath=str(axis_path.parent),
        )

        logger.info(f"Generated HDL files in {output_dir}")
        return segment_path, acc_path, axis_path

    @staticmethod
    def _build_verilog_params(config: dict) -> RSAXISVerilogParameters:
        """Build RSAXISVerilogParameters from config dictionary"""
        # For simplicity, use the first ecc_len and word_size if arrays
        ecc_len = config.get("ecc_len", 8)
        if isinstance(ecc_len, list):
            ecc_len = ecc_len[0]

        word_size = config.get("word_size", 8)
        if isinstance(word_size, list):
            word_size = word_size[0]

        params: RSAXISVerilogParameters = {
            "irreducible_poly_coeffs": galois.irreducible_poly(2, word_size).coeffs,
            "word_size": word_size,
            "n_parity_sym": ecc_len,
        }

        return params


class SynthesisWorker:
    """Worker class for synthesis of individual configurations"""

    def __init__(self, hdl_files: tuple[Path, Path, Path]):
        """
        Initialize synthesis worker.

        Args:
            hdl_files: Tuple of (segment_path, accumulator_path, axis_path)
        """
        self.hdl_files = hdl_files

    def synthesize(self, config: dict) -> ResourceReport:
        """
        Synthesize a single configuration.

        Args:
            config: Configuration dictionary

        Returns:
            ResourceReport with results
        """
        config_name = config.get("name", "unknown")
        target_str = config.get("target", "xilinx")

        try:
            # Validate target
            target = SynthTarget(target_str.lower())

            # Create work directory
            work_dir = proj_path / "build" / "yosys" / config_name
            work_dir.mkdir(parents=True, exist_ok=True)

            # Run synthesis
            logger.info(f"Synthesizing {config_name} for target {target.value}")
            wrapper = YosysWrapper(work_dir)
            yosys_log = wrapper.run(
                sources=list(self.hdl_files),
                top_module="RS_AXIS",
                synth_target=target,
            )

            # Parse results
            report = self._parse_yosys_log(yosys_log, config_name, target_str)
            report.yosys_log_path = str(work_dir / "yosys.log")

            logger.info(
                f"✓ Synthesis successful for {config_name}: "
                f"LUT={report.num_lut}, FF={report.num_ff}, BRAM={report.num_bram}"
            )

            return report

        except Exception as e:
            logger.error(f"✗ Synthesis failed for {config_name}: {e}")
            return ResourceReport(
                config_name=config_name,
                target=target_str,
                success=False,
                error_message=str(e),
            )

    def _parse_yosys_log(self, log_content: str, config_name: str, target: str) -> ResourceReport:
        """
        Parse Yosys log output to extract resource metrics.
        Supports both JSON and text-based formats.

        Args:
            log_content: Raw Yosys log output
            config_name: Name of configuration
            target: Target platform

        Returns:
            ResourceReport with parsed metrics
        """
        report = ResourceReport(config_name=config_name, target=target, success=True)

        # Try to parse JSON format first
        json_data = self._extract_json_from_log(log_content)
        assert json_data
        self._parse_json_stats(json_data, report)

        # Map specific cell types to common metrics based on target
        self._map_cell_types_to_metrics(report, target)

        # Parse max frequency (if available)
        freq_match = re.search(r"Max frequency:\s*([\d.]+)\s*MHz", log_content, re.IGNORECASE)
        if freq_match:
            report.max_freq_mhz = float(freq_match.group(1))

        return report

    def _extract_json_from_log(self, log_content: str) -> dict | None:
        """
        Extract JSON statistics from Yosys log output.

        Args:
            log_content: Raw Yosys log output

        Returns:
            Parsed JSON dict or None if not found
        """
        # Find JSON block in log (typically contains "modules" or "design" keys)
        json_pattern = r"\{\s*\"creator\".*?\}\s*(?=\n\n|End of script)"
        json_match = re.search(json_pattern, log_content, re.DOTALL)

        if json_match:
            try:
                json_str = json_match.group(0)
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON from Yosys log: {e}")
                return None

        return None

    def _parse_json_stats(self, json_data: dict, report: ResourceReport) -> None:
        """
        Parse statistics from Yosys JSON output format.

        Args:
            json_data: Parsed JSON statistics from Yosys
            report: ResourceReport to populate
        """
        # Use the 'design' section if available, otherwise use first module
        stats = json_data.get("design", {})
        if not stats and "modules" in json_data:
            # Get the first (and usually only) module
            modules = json_data["modules"]
            stats = next(iter(modules.values())) if modules else {}

        # Extract basic metrics
        report.num_wires = stats.get("num_wires", 0)
        report.num_wire_bits = stats.get("num_wire_bits", 0)
        report.num_public_wires = stats.get("num_pub_wires", 0)
        report.num_public_wire_bits = stats.get("num_pub_wire_bits", 0)
        report.num_memories = stats.get("num_memories", 0)
        report.num_memory_bits = stats.get("num_memory_bits", 0)
        report.num_processes = stats.get("num_processes", 0)
        report.num_cells = stats.get("num_cells", 0)

        # Extract cell types
        num_cells_by_type = stats.get("num_cells_by_type", {})
        report.custom_cells = dict(num_cells_by_type)

    def _map_cell_types_to_metrics(self, report: ResourceReport, target: str) -> None:
        """
        Map custom cell types to standard metrics based on target platform.

        Args:
            report: ResourceReport to update
            target: Target platform (xilinx, ecp5, ice40, nexus, gowin, etc.)
        """
        target_lower = target.lower()

        # ECP5 specific
        if "ecp5" in target_lower:
            # LUT4 and LUT are the lookup tables
            report.num_lut = report.custom_cells.get("LUT4", 0)
            # TRELLIS_FF are the flip-flops
            report.num_ff = report.custom_cells.get("TRELLIS_FF", 0)
            # BRAM cells (DP16KD, TRELLIS_DPR16X4, etc.)
            report.num_bram = report.custom_cells.get("DP16KD", 0) + report.custom_cells.get(
                "TRELLIS_DPR16X4", 0
            )
        # Nexus specific (Lattice Nexus devices)
        elif "nexus" in target_lower:
            # LUT4 is the lookup table in Nexus architecture
            report.num_lut = report.custom_cells.get("LUT4", 0)
            # FD1P3IX, FD1P3BX are flip-flop variants in Nexus
            report.num_ff = (
                report.custom_cells.get("FD1P3IX", 0)
                + report.custom_cells.get("FD1P3BX", 0)
                + report.custom_cells.get("FD1P3AX", 0)
            )
            # WIDEFN9, WIDEFN_LOGIC are wide function cells
            # These might contribute to LUT count depending on synthesis
            report.metadata["wide_logic_cells"] = report.custom_cells.get("WIDEFN9", 0)
            # Block RAM cells (DPR16X4, DPRF512, etc.)
            report.num_bram = report.custom_cells.get("DPR16X4", 0) + report.custom_cells.get("DPRF512", 0)
        # ICE40 specific
        elif "ice40" in target_lower:
            # SB_LUT4 is the lookup table
            report.num_lut = report.custom_cells.get("SB_LUT4", 0)
            # SB_DFF, SB_DFFE are the flip-flops
            report.num_ff = report.custom_cells.get("SB_DFF", 0) + report.custom_cells.get("SB_DFFE", 0)
            # SB_RAM40_4K, SB_RAM40_4KNRNW are BRAM
            report.num_bram = report.custom_cells.get("SB_RAM40_4K", 0) + report.custom_cells.get(
                "SB_RAM40_4KNRNW", 0
            )
        # Xilinx specific
        elif "xilinx" in target_lower:
            # LUT6, LUT5, LUT4 are lookup tables
            report.num_lut = (
                report.custom_cells.get("LUT6", 0)
                + report.custom_cells.get("LUT5", 0)
                + report.custom_cells.get("LUT4", 0)
            )
            # FDRE, FDR, FDS are flip-flops
            report.num_ff = (
                report.custom_cells.get("FDRE", 0)
                + report.custom_cells.get("FDR", 0)
                + report.custom_cells.get("FDS", 0)
            )
            # BRAM36E1, BRAM18E1 are block RAM
            report.num_bram = report.custom_cells.get("BRAM36E1", 0) + report.custom_cells.get("BRAM18E1", 0)
        # GOWIN specific
        elif "gowin" in target_lower:
            # LUT is the lookup table
            report.num_lut = report.custom_cells.get("LUT", 0)
            # DFF, DFFE are flip-flops
            report.num_ff = report.custom_cells.get("DFF", 0) + report.custom_cells.get("DFFE", 0)
            # BRAM is block RAM
            report.num_bram = report.custom_cells.get("BRAM", 0)
        # Fallback: try common names
        else:
            report.num_lut = report.custom_cells.get("LUT4", 0) + report.custom_cells.get("LUT", 0)
            report.num_ff = report.custom_cells.get("TRELLIS_FF", 0) + report.custom_cells.get("FD1P3IX", 0)
            report.num_bram = report.custom_cells.get("BRAM", 0)


class ResourceAggregator:
    """Aggregate resource reports across configurations"""

    @staticmethod
    def summarize(reports: list[ResourceReport], output_path: str | Path | None = None) -> dict:
        """
        Aggregate resource reports and generate summary.

        Args:
            reports: List of ResourceReport objects
            output_path: Path to save summary JSON (default: build/yosys/summary.json)

        Returns:
            Summary dictionary
        """
        output_path = Path(output_path) if output_path else proj_path / "build" / "yosys" / "summary.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        successful = [r for r in reports if r.success]
        failed = [r for r in reports if not r.success]

        summary = {
            "total_configs": len(reports),
            "successful_configs": len(successful),
            "failed_configs": len(failed),
            "reports": [r.to_dict() for r in reports],
        }

        # Save summary
        with Path.open(output_path, "w") as f:
            json.dump(summary, f, indent=2)

        logger.info(f"Summary saved to {output_path}")
        logger.info(f"Synthesis results: {len(successful)} successful, {len(failed)} failed")

        return summary


class ResourceEstimator:
    """
    Main orchestrator for resource estimation pipeline.

    Coordinates:
    1. Configuration loading
    2. HDL generation
    3. Multi-threaded synthesis
    4. Result aggregation
    """

    def __init__(self, config_path: str | Path = "resources/config.json", max_workers: int = 4):
        """
        Initialize ResourceEstimator.

        Args:
            config_path: Path to configuration JSON file
            max_workers: Maximum number of synthesis threads
        """
        self.config_path = Path(config_path)
        self.max_workers = max_workers
        self.reports: list[ResourceReport] = []
        self.reports_lock = Lock()

        logger.info(f"Initialized ResourceEstimator with {max_workers} workers")

    def estimate(self) -> Path:
        """
        Execute the full resource estimation pipeline.

        Returns:
            Path to summary.json
        """
        logger.info("=" * 70)
        logger.info("Starting Resource Estimation Pipeline")
        logger.info("=" * 70)

        try:
            # Phase 1: Load configuration
            logger.info("\n[Phase 1] Loading configuration...")
            configs = ConfigLoader.load(self.config_path)
            logger.info(f"✓ Loaded {len(configs)} configurations")

            # Phase 2: Generate HDL
            logger.info("\n[Phase 2] Generating HDL...")
            hdl_files = GenerationManager.generate_hdl(configs)
            logger.info("✓ HDL generation complete")

            # Phase 3: Multi-threaded synthesis
            logger.info("\n[Phase 3] Running multi-threaded synthesis...")
            self._run_synthesis_workers(configs, hdl_files)
            logger.info(f"✓ Synthesis complete ({len(self.reports)} configurations)")

            # Phase 4: Aggregation & reporting
            logger.info("\n[Phase 4] Aggregating results...")
            summary_path = proj_path / "build" / "yosys" / "summary.json"
            summary = ResourceAggregator.summarize(self.reports, summary_path)
            logger.info("✓ Aggregation complete")

            logger.info("\n" + "=" * 70)
            logger.info("Resource Estimation Pipeline Complete")
            logger.info("=" * 70)
            logger.info(f"\nResults saved to: {summary_path}")
            logger.info(
                f"Total: {summary['total_configs']} configs, "
                f"{summary['successful_configs']} successful, "
                f"{summary['failed_configs']} failed\n"
            )

            return summary_path

        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            raise

    def _run_synthesis_workers(self, configs: list[dict], hdl_files: tuple[Path, Path, Path]) -> None:
        """
        Run synthesis workers in parallel thread pool.

        Args:
            configs: List of configuration dictionaries
            hdl_files: Tuple of (segment_path, accumulator_path, axis_path)
        """
        worker = SynthesisWorker(hdl_files)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all synthesis tasks
            future_to_config = {executor.submit(worker.synthesize, config): config for config in configs}

            # Collect results as they complete
            for future in as_completed(future_to_config):
                config = future_to_config[future]
                try:
                    report = future.result()
                    with self.reports_lock:
                        self.reports.append(report)
                except Exception as e:
                    logger.error(f"Worker exception for {config.get('name')}: {e}")
                    with self.reports_lock:
                        self.reports.append(
                            ResourceReport(
                                config_name=config.get("name", "unknown"),
                                target=config.get("target", "unknown"),
                                success=False,
                                error_message=str(e),
                            )
                        )


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.WARN,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    estimator = ResourceEstimator(
        config_path="resources/config.json",
        max_workers=4,
    )
    summary_path = estimator.estimate()
    print(f"\nSummary saved to: {summary_path}")
