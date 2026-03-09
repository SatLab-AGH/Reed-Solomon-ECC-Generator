from dataclasses import asdict, dataclass
from pathlib import Path
import json
import math
from typing import List, Union
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import brentq


@dataclass(slots=True)
class BERCurve:
    data_len: int
    ecc_len: int
    word_size: int
    ber_min: float
    ber_max: float
    input_ber_lst: list[float]
    output_ber_lst: list[float]

    def __post_init__(self):
        if len(self.input_ber_lst) != len(self.output_ber_lst):
            raise ValueError("input_ber and output_ber length mismatch")

    @staticmethod
    def load_ber_json(path: str | Path) -> list[object]:
        raw = json.loads(Path(path).read_text())
        return [BERCurve(**entry) for entry in raw]

    @staticmethod
    def append_ber_json(path: Union[str, Path], ber_curves: List[object]):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if path.exists():
            try:
                raw = json.loads(path.read_text())
            except json.JSONDecodeError:
                raw = []
        else:
            raw = []

        if not isinstance(raw, list):
            raise ValueError(f"Existing JSON at {path} is not a list")

        for curve in ber_curves:
            raw.append(asdict(curve))  # pyright: ignore[reportArgumentType]

        path.write_text(json.dumps(raw, indent=4))

    @staticmethod
    def clear_ber_json(path: Union[str, Path]):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)  # ensure directory exists
        path.write_text(json.dumps([], indent=4))


def binary_entropy(p):
    if p == 0 or p == 1:
        return 0
    return -p * np.log2(p) - (1 - p) * np.log2(1 - p)


def get_shannon_threshold(rate):
    """Finds the maximum input BER (p) for a given code rate using brentq solver."""
    if rate >= 1:
        return 0
    # We want to solve: 1 - H(p) - rate = 0
    objective = lambda p: 1 - binary_entropy(p) - rate
    # The threshold p will be between 0 and 0.5
    return brentq(objective, 1e-9, 0.5)


def plot_ber_tiles(curves: list[BERCurve], save_path: str | Path | None = None, dpi=300):
    # group curves by word_size
    groups = {}
    for c in curves:
        groups.setdefault(c.word_size, []).append(c)

    word_sizes = sorted(groups)

    n = len(word_sizes)
    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)

    fig, axes = plt.subplots(rows, cols, squeeze=False, figsize=(cols * 5, rows * 4))
    axes = axes.flatten()

    for ax, ws in zip(axes, word_sizes):
        plotted_limits = set()

        # --- NEW: ADD "NO ECC" REFERENCE LINE (y=x) ---
        # We find the min/max of the data to make sure the line spans the plot
        all_inputs = [val for c in groups[ws] for val in c.input_ber_lst]
        if all_inputs:
            ref_min, ref_max = min(all_inputs), max(all_inputs)
            ax.plot(
                [ref_min, ref_max],
                [ref_min, ref_max],
                color="black",
                linestyle="--",
                linewidth=1,
                alpha=0.7,
                label="No ECC (y=x)",
                zorder=1,  # Keep it behind the data curves
            )

        for c in groups[ws]:
            (line,) = ax.plot(
                c.input_ber_lst,
                c.output_ber_lst,
                marker="o",
                markersize=4,
                label=f"Measured ({c.data_len + c.ecc_len}, {c.data_len})",
                zorder=3,
            )

            # Shannon Limit Logic
            rate = c.data_len / (c.data_len + c.ecc_len)
            if rate not in plotted_limits:
                threshold = get_shannon_threshold(rate)
                ax.axvline(
                    x=threshold,
                    color=line.get_color(),
                    linestyle=":",  # Dotted to distinguish from y=x
                    alpha=0.5,
                    label=f"Shannon (R={rate:.2f})",
                    zorder=2,
                )
                plotted_limits.add(rate)

        ax.set_title(f"word_size = {ws}")
        ax.set_xlabel("Input BER")
        ax.set_ylabel("Output BER")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.grid(True, which="both", linestyle=":", alpha=0.4)
        ax.legend(fontsize=7, loc="upper left")  # Moved to lower right to avoid y=x line

    # hide unused axes
    for ax in axes[len(word_sizes) :]:
        ax.set_visible(False)

    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=dpi, bbox_inches="tight")
    plt.show()


def main():
    json_path = Path(__file__).parent / "ber_curve.json"
    fig_path = Path(__file__).parent / "figure.png"
    curves: list[BERCurve] = BERCurve.load_ber_json(json_path)  # pyright: ignore[reportAssignmentType]
    plot_ber_tiles(curves, save_path=fig_path)


if __name__ == "__main__":
    main()
