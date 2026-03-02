import abc
from dataclasses import dataclass
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Literal, NotRequired, Required, Sequence, TypedDict

from generators.FileVerilog import FileVerilogGenerator, FileVerilogParameters

logger = logging.getLogger(__name__)
proj_path = Path(__file__).resolve().parent.parent


class ModuleVerilogParameters(FileVerilogParameters):
    dependencies: NotRequired[str]
    additional_comments: NotRequired[str]
    specific_params: NotRequired[str]
    create_date: NotRequired[datetime]


@dataclass
class ModuleParameter:
    name: str
    par_type: str | None = None
    default_value: int | str | None = None

    def __str__(self) -> str:
        type_part = f"{self.par_type} " if self.par_type is not None else ""
        default_part = f" = {self.default_value}" if self.default_value is not None else ""
        return f"parameter {type_part}{self.name}{default_part}"


@dataclass
class ModuleInterface:
    name: str
    intr_type: Literal["i", "o", "io"]
    width: int | None = None
    is_reg: bool | None = None

    def __str__(self) -> str:
        intr_map = {"i": "input", "o": "output", "io": "inout"}

        intr_type = intr_map.get(self.intr_type, self.intr_type)
        reg_or_wire = "reg" if self.is_reg else "wire"
        width = f"[{self.width - 1}:0]" if self.width is not None else ""

        return f"{intr_type} {reg_or_wire} {width} {self.name}".replace("  ", " ").strip()


class ModuleVerilogGenerator(FileVerilogGenerator):
    def __init__(self, params: ModuleVerilogParameters) -> None:
        super().__init__(params)
        self.params = params
        self._load_global_file_config()
        self.design_name = None

    @staticmethod
    def flatten_interfaces(
        interfaces: Sequence[ModuleInterface | tuple[ModuleInterface, ...]],
    ) -> list[ModuleInterface]:
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
        parameters: list[ModuleParameter] | None = None,
    ):
        self.verilog_interfaces = interfaces
        self.verilog_parameters = parameters

        m_head = [f"module {self.design_name}"]

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

        m_head = [f"{self.design_name}"]

        # ---------- parameters ----------
        if parameters:
            m_head.append("# (")
            for i, parameter in enumerate(parameters):
                comma = "," if i < len(parameters) - 1 else ""
                m_head.append(f"\t.{parameter.name}({{{parameter.name}}}){comma}")
            m_head.append(")")

        m_head.append(f"{self.design_name}_{{instance_name}}_impl")
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

    def _generate(self):
        pass
