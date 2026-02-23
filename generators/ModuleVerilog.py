import abc
import json
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import NotRequired, Required, TypedDict

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
proj_path = Path(__file__).resolve().parent.parent
handle = RotatingFileHandler(
    proj_path.joinpath("logs/mastrovitoverilog.log"), maxBytes=5 * 1024 * 1024, backupCount=3
)
formatter = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(funcName)s | %(message)s"
)
handle.setFormatter(formatter)
logger.addHandler(handle)


class ModuleVerilogParameters(TypedDict):
    company: NotRequired[str]
    engineer: NotRequired[str]
    project_name: NotRequired[str]
    design_name: Required[str]
    description: NotRequired[str]
    output_path: Required[Path]
    dependencies: NotRequired[str]
    additional_comments: NotRequired[str]
    specific_params: NotRequired[str]
    create_date: NotRequired[datetime]


class ModuleVerilogGenerator(abc.ABC):
    def __init__(self, params: ModuleVerilogParameters) -> None:
        self.params = params
        self._load_global_config()

    def _load_global_config(self, path=None):
        path = Path(__file__).parent.resolve() if path is None else path
        file_string = ""
        with Path.open(Path.joinpath(path, "config.json")) as file:
            file_string = file.read()
        global_config = json.loads(file_string)
        global_config["create_date"] = datetime.now()
        self.params |= global_config

    @abc.abstractmethod
    def _generate_module(self, *args, **kwargs) -> str:
        pass

    # File
    @staticmethod
    def _generate_file_header_template() -> str:
        return (
            f"{'//' * 20}\n"
            + "// Company: {company}\n"
            + "// Engineer: {engineer}\n"
            + "// Create Date: {create_date}\n"
            + "// Design Name: {design_name}\n"
            + "// Project Name: {project_name}\n"
            + "// Description: {description}\n"
            + "// Dependencies: {dependencies}\n"
            + "// \n"
            + "// Design Specific Parameters: {specific_params} \n"
            + "// Additional Comments: {additional_comments}\n"
            + f"{'//' * 20} \n\r\n\r"
            + "`timescale 1ns/1ps\n\n"
        )

    @abc.abstractmethod
    def _generate_file_header(self) -> str:
        pass

    def print_verilog_file(self):
        file_name = f"{self.params['design_name']}.v"

        path = proj_path.joinpath(self.params["output_path"])

        Path(path).mkdir(exist_ok=True, parents=True)

        with Path.open(Path.joinpath(path, file_name), "w") as file:
            logger.info(f"Generating Verilog File: {path}")
            file.write(self._generate_file_header())

            file.write(self._generate_module())