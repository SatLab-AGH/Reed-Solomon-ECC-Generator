set -e

source ./.venv/bin/activate

cd src

python3 -m generators.MastrovitoMatrix
echo "Generated MastrovitoMatrix"
python3 -m generators.MastrovitoVerilog
echo "Generated MastrovitoVerilog"
python3 -m generators.RSSegmentVerilog
echo "Generated RSSegmentVerilog"
python3 -m generators.RSAccumulatorVerilog
echo "Generated RSAccumulatorVerilog"
python3 -m generators.RSAXISVerilog
echo "Generated RSAXISVerilog"

cd -
return 0