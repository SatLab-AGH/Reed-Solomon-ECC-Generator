set -eu

source ./.venv/bin/activate

cd src

python3 -m generators.MastrovitoMatrix
python3 -m generators.MastrovitoVerilog
python3 -m generators.RSSegmentVerilog
python3 -m generators.RSAccumulatorVerilog
python3 -m generators.RSAXISVerilog

cd -