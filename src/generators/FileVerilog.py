import abc
from dataclasses import dataclass
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import NotRequired, TypedDict

logger = logging.getLogger(__name__)


class FileVerilogParameters(TypedDict):
    company: NotRequired[str]
    engineer: NotRequired[str]
    project_name: NotRequired[str]


class FileVerilogGenerator(abc.ABC):
    def __init__(self, params: FileVerilogParameters) -> None:
        self.params = params

        self.company: str | None = params.get("company")
        self.engineer: str | None = params.get("engineer")
        self.project_name: str | None = params.get("project_name")
        self.design_name: str | None = None
        self.description: str | None = None
        self.dependencies: str | None = None
        self.specific_params: str | None = None

        self.filename = str(self.design_name) + ".v"
        self.filepath = Path(__file__).resolve()
        self.template_path = self.filepath.parent / "templates"
        self.proj_path = Path(__file__).resolve().parent.parent.parent
        self.build_path = self.proj_path / "build"
        self.rtl_build_path = self.build_path / "rtl"

    # File
    def _get_file_header_template(self) -> str:
        with open(self.template_path / "file_header.txt", "r", encoding="utf-8") as f:
            template = f.read()
        return template

    def _generate_file_header(self) -> str:
        template = self._get_file_header_template()

        return template.format(
            create_date=datetime.now().strftime("%Y-%m-%d %H:%M"),
            company=self.company,
            engineer=self.engineer,
            project_name=self.project_name,
            design_name=self.design_name,
            description=self.description,
            dependencies=self.dependencies,
            specific_params=self.specific_params,
        )

    def generate_to_dir(self, dir: str | Path | None = None):
        dir = "" if dir is None else dir
        path = self.rtl_build_path.joinpath(dir).joinpath(str(self.design_name) + ".v")

        Path(path.parent).mkdir(exist_ok=True, parents=True)

        with Path.open(path, "w") as file:
            logger.info(f"Generating Verilog File: {path}")
            file.write(self._generate_file_header())

            file.write(self._generate_module())

    @abc.abstractmethod
    def _generate_module(self) -> str:
        pass
