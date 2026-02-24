import abc
from dataclasses import dataclass
import json
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Literal, NotRequired, Required, Sequence, TypedDict
import inspect

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

@dataclass
class ModuleParameter:
    name: str
    par_type: str|None = None
    default_value: int|str|None = None

    def __str__(self) -> str:
        type_part = f"{self.par_type} " if self.par_type is not None else ""
        default_part = f" = {self.default_value}" if self.default_value is not None else ""
        return f"parameter {type_part}{self.name}{default_part}"

@dataclass
class ModuleInterface:
    name: str
    intr_type: Literal['i', 'o', 'io']
    width: int|None = None
    is_reg: bool|None = None 

    def __str__(self) -> str:
        intr_map = {
            "i": "input",
            "o": "output",
            "io": "inout"
        }

        intr_type = intr_map.get(self.intr_type, self.intr_type)
        reg_or_wire = "reg" if self.is_reg else "wire"
        width = f"[{self.width-1}:0]" if self.width is not None else ""

        return f"{intr_type} {reg_or_wire} {width} {self.name}".replace("  ", " ").strip()


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
        global_config["create_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.params |= global_config

    @staticmethod
    def flatten_interfaces(interfaces: Sequence[ModuleInterface | tuple[ModuleInterface, ...]]) -> list[ModuleInterface]:
        flat_interfaces_ls = []
        for entry in interfaces:
            if isinstance(entry, tuple):
                flat_interfaces_ls.extend(entry)
            else:
                flat_interfaces_ls.append(entry)
        return flat_interfaces_ls

    def generic_generate_module_header(
        self,
        interfaces: Sequence[ModuleInterface | tuple[ModuleInterface, ...]],
        parameters: list[ModuleParameter] | None = None
    ):
        self.verilog_interfaces = interfaces
        self.verilog_parameters = parameters

        m_head = [f'module {self.params["design_name"]}']

        # ---------- parameters ----------
        if parameters:
            m_head.append("# (")
            for i, parameter in enumerate(parameters):
                comma = "," if i < len(parameters) - 1 else ""
                m_head.append(f"\t{parameter}{comma}")
            m_head.append(")")

        m_head.append("(")

        # ---------- interfaces ----------
        # flatten for comma logic
        flat_interfaces = self.flatten_interfaces(interfaces)

        flat_index = 0

        for g_i, entry in enumerate(interfaces):

            group = entry if isinstance(entry, tuple) else (entry,)

            for iface in group:
                comma = "," if flat_index < len(flat_interfaces) - 1 else ""
                m_head.append(f"\t{iface}{comma}")
                flat_index += 1

            # blank line between groups (not after last)
            if g_i < len(interfaces) - 1:
                m_head.append("")

        m_head.append(");\n\n")

        return "\n".join(m_head)

    def generic_generate_module_instance_template(
        self,
    ):
        parameters = self.verilog_parameters
        interfaces = self.verilog_interfaces

        m_head = [f'{self.params["design_name"]}']

        # ---------- parameters ----------
        if parameters:
            m_head.append("# (")
            for i, parameter in enumerate(parameters):
                comma = "," if i < len(parameters) - 1 else ""
                m_head.append(f"\t.{parameter.name}({{{parameter.name}}}){comma}")
            m_head.append(")")
        
        m_head.append(f"{self.params["design_name"]}_{{instance_name}}_impl")
        m_head.append("(")

        # ---------- interfaces ----------
        # flatten for comma logic
        flat_interfaces = self.flatten_interfaces(interfaces)

        flat_index = 0

        for g_i, entry in enumerate(interfaces):

            group = entry if isinstance(entry, tuple) else (entry,)

            for iface in group:
                comma = "," if flat_index < len(flat_interfaces) - 1 else ""
                m_head.append(f"\t.{iface.name}({{{iface.name}}}){comma}")
                flat_index += 1

            # blank line between groups (not after last)
            if g_i < len(interfaces) - 1:
                m_head.append("")

        m_head.append(");\n\n")

        return "\n".join(m_head)

    @abc.abstractmethod
    def _generate_module(self, *args, **kwargs) -> str:
        pass

    # File
    @staticmethod
    def _get_file_header_template() -> str:
        with open("generators/templates/file_header.txt", "r", encoding="utf-8") as f:
            template = f.read()
        return template

    def _generate_file_header(self) -> str:
        template = self._get_file_header_template()
        config = self.params

        return template.format(
            company=config.get("company"),
            engineer=config.get("engineer"),
            create_date=config.get("create_date"),
            design_name=config.get("design_name"),
            project_name=config.get("project_name"),
            description=config.get("description"),
            dependencies=config.get("dependencies"),
            specific_params=config.get("specific_params"),
            additional_comments=config.get("additional_comments"),
        )
    
    def _generate(self):
        pass

    def generate_to_file(self):
        file_name = f"{self.params['design_name']}.v"

        path = proj_path.joinpath(self.params["output_path"])

        Path(path).mkdir(exist_ok=True, parents=True)

        with Path.open(Path.joinpath(path, file_name), "w") as file:
            logger.info(f"Generating Verilog File: {path}")
            file.write(self._generate_file_header())

            file.write(self._generate_module())
