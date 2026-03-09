set -euo pipefail

cd src

uv run python3 -m generators.MastrovitoMatrix
echo "Generated MastrovitoMatrix"
uv run python3 -m generators.MastrovitoVerilog
echo "Generated MastrovitoVerilog"
uv run python3 -m generators.RSSegmentVerilog
echo "Generated RSSegmentVerilog"
uv run python3 -m generators.RSAccumulatorVerilog
echo "Generated RSAccumulatorVerilog"
uv run python3 -m generators.RSAXISVerilog
echo "Generated RSAXISVerilog"

cd -