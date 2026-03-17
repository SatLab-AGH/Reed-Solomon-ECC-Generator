import subprocess
from enum import Enum
from pathlib import Path


class SynthTarget(Enum):
    """Supported synthesis targets"""

    ICE40 = "ice40"
    ECP5 = "ecp5"
    NEXUS = "nexus"
    XILINX = "xilinx"
    GOWIN = "gowin"


class YosysWrapper:
    """
    Thin wrapper around Yosys process execution.
    Handles script generation, process invocation, and raw log output.
    """

    def __init__(self, work_dir: str | Path | None = None):
        """
        Initialize Yosys wrapper.

        Args:
            work_dir: Working directory for temporary files (default: current directory)
        """
        self.work_dir = Path(work_dir) if work_dir else Path.cwd()
        self.work_dir.mkdir(parents=True, exist_ok=True)

        self.logfile = self.work_dir / "yosys.log"
        self.script_file = self.work_dir / "script.yos"

    def run(
        self,
        sources: str | Path | list[str | Path],
        top_module: str,
        synth_target: SynthTarget | str,
    ) -> str:
        """
        Run Yosys synthesis and return raw log output.

        Args:
            sources: Path(s) to Verilog/VHDL source files or directory
            top_module: Top-level module name
            synth_target: Target FPGA platform (ICE40, ECP5, NEXUS, XILINX, GOWIN)

        Returns:
            Raw Yosys log output as string
        """
        if isinstance(synth_target, str):
            synth_target = SynthTarget(synth_target.lower())

        # Find source files
        verilog_files = self._find_source_files(sources)
        if not verilog_files:
            raise FileNotFoundError(f"No Verilog/VHDL files found in {sources}")

        # Generate Yosys script
        script_content = self._generate_script(verilog_files, top_module, synth_target)
        self.script_file.write_text(script_content)

        # Execute Yosys
        try:
            result = subprocess.run(
                ["yosys", "-ql", str(self.logfile), "-p", f"script {self.script_file}"],
                capture_output=True,
                text=True,
                timeout=300,
                check=True,
            )

            if result.returncode != 0:
                raise RuntimeError(
                    f"Yosys synthesis failed with code {result.returncode}\nStderr: {result.stderr}"
                )

        except FileNotFoundError as e:
            raise RuntimeError("Yosys not found. Please install Yosys.") from e

        # Return raw log content
        return self.logfile.read_text()

    def _find_source_files(self, sources: str | Path | list[str | Path]) -> list[Path]:
        """Find all Verilog/VHDL source files"""
        files = []

        if isinstance(sources, (str, Path)):
            sources = [sources]

        for src in sources:
            src_path = Path(src)
            if src_path.is_file():
                files.append(src_path)
            elif src_path.is_dir():
                files.extend(src_path.glob("**/*.v"))
                files.extend(src_path.glob("**/*.vhdl"))
                files.extend(src_path.glob("**/*.vhd"))

        return sorted(set(files))

    def _generate_script(
        self, verilog_sources: list[Path], top_module: str, synth_target: SynthTarget
    ) -> str:
        """Generate Yosys synthesis script"""
        script_lines = [
            f"# Yosys synthesis script for {top_module}",
            f"# Target: {synth_target.value}",
            "",
        ]

        # Add source files
        for vfile in verilog_sources:
            if vfile.suffix.lower() == ".v":
                script_lines.append(f"read -vlog2k {vfile}")
            elif vfile.suffix.lower() in [".vhdl", ".vhd"]:
                script_lines.append(f"read -vhdl {vfile}")

        # Hierarchy and optimization
        script_lines.extend(
            [
                "",
                "# Hierarchy and optimization",
                f"hierarchy -top {top_module}",
                "proc",
                "opt",
                "",
            ]
        )

        # Synthesis command
        script_lines.append(f"synth_{synth_target.value} -top {top_module}")
        script_lines.extend(["", "stat -json"])

        return "\n".join(script_lines) + "\n"


if __name__ == "__main__":
    estimator = YosysWrapper(Path(__file__).parent.parent / "/build/yosys")
    stats = estimator.run(
        [
            "./build/rtl/yosys/RS_Accumulator.v",
            "./build/rtl/yosys/RS_AXIS.v",
            "./build/rtl/yosys/RS_Segment.v",
        ],
        top_module="RS_AXIS",
        synth_target=SynthTarget("xilinx"),
    )
    print(stats)
