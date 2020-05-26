from typing import Union

from janis_core.graph.node import NodeType

from janis_core.types import get_instantiated_type

from janis_core.utils import first_value

from janis_core.utils.errors import (
    TooManyArgsException,
    IncorrectArgsException,
    InvalidByProductException,
    ConflictingArgumentsException,
)
from janis_core.utils.logger import Logger
from janis_core.types.common_data_types import Array, String, File, Directory, Int

from janis_core.utils.bracketmatching import get_keywords_between_braces
from abc import ABC, abstractmethod


class Selector(ABC):
    @staticmethod
    def is_selector():
        return True

    @abstractmethod
    def returntype(self):
        pass

    def __neg__(self):
        from janis_core.operators.logical import NotOperator

        return NotOperator(self)

    @abstractmethod
    def to_string_formatter(self):
        pass

    def __and__(self, other):
        from janis_core.operators.logical import AndOperator

        return AndOperator(self, other)

    def __rand__(self, other):
        from janis_core.operators.logical import AndOperator

        return AndOperator(other, self)

    def __or__(self, other):
        from janis_core.operators.logical import OrOperator

        return OrOperator(self, other)

    def __ror__(self, other):
        from janis_core.operators.logical import OrOperator

        return OrOperator(other, self)

    def __add__(self, other):
        from janis_core.operators.logical import AddOperator

        return AddOperator(self, other)

    def __radd__(self, other):
        from janis_core.operators.logical import AddOperator

        return AddOperator(other, self)

    def __sub__(self, other):
        from janis_core.operators.logical import SubtractOperator

        return SubtractOperator(self, other)

    def __rsub__(self, other):
        from janis_core.operators.logical import SubtractOperator

        return SubtractOperator(other, self)

    def __mul__(self, other):
        from janis_core.operators.logical import MultiplyOperator

        return MultiplyOperator(self, other)

    def __rmul__(self, other):
        from janis_core.operators.logical import MultiplyOperator

        return MultiplyOperator(other, self)

    def __truediv__(self, other):
        from janis_core.operators.logical import DivideOperator

        return DivideOperator(self, other)

    def __rtruediv__(self, other):
        from janis_core.operators.logical import DivideOperator

        return DivideOperator(other, self)

    # def __eq__(self, other):
    def equals(self, other):
        from janis_core.operators.logical import EqualityOperator

        return EqualityOperator(self, other)

    def __ne__(self, other):
        from janis_core.operators.logical import EqualityOperator

        return EqualityOperator(self, other)

    def __gt__(self, other):
        from janis_core.operators.logical import GtOperator

        return GtOperator(self, other)

    def __ge__(self, other):
        from janis_core.operators.logical import GteOperator

        return GteOperator(self, other)

    def __lt__(self, other):
        from janis_core.operators.logical import LtOperator

        return LtOperator(self, other)

    def __le__(self, other):
        from janis_core.operators.logical import LteOperator

        return LteOperator(self, other)

    def __len__(self):
        from janis_core.operators.standard import LengthOperator

        return LengthOperator(self)

    def as_str(self):
        from janis_core.operators.operator import AsStringOperator

        return AsStringOperator(self)

    def as_bool(self):
        from janis_core.operators.operator import AsBoolOperator

        return AsBoolOperator(self)

    def as_int(self):
        from janis_core.operators.operator import AsIntOperator

        return AsIntOperator(self)

    def op_and(self, other):
        from janis_core.operators.logical import AndOperator

        return AndOperator(self, other)

    def op_or(self, other):
        from janis_core.operators.logical import OrOperator

        return OrOperator(self, other)

    def __getitem__(self, item):
        from janis_core.operators.operator import IndexOperator

        return IndexOperator(self, item)

    def basename(self):
        from .standard import BasenameOperator

        outtype = self.returntype()
        if not isinstance(outtype, (File, Directory)):
            raise Exception(
                "Basename operator can only be applied to steps of File / Directory type, received: "
                + str(outtype)
            )

        return BasenameOperator(self)


SelectorOrValue = Union[Selector, int, str, float]


class InputSelector(Selector):
    def __init__(self, input_to_select, use_basename=None):
        # maybe worth validating the input_to_select identifier
        self.input_to_select = input_to_select
        self.use_basename = use_basename

    def returntype(self):
        # Todo: Work out how this can be achieved
        return File

    def to_string_formatter(self):
        kwarg = {self.input_to_select: self}
        from janis_core.operators.stringformatter import StringFormatter

        return StringFormatter(f"{{{self.input_to_select}}}", **kwarg)


class InputNodeSelector(Selector):
    def __init__(self, input_node):
        from janis_core.workflow.workflow import InputNode

        if input_node.node_type != NodeType.INPUT:  # input
            raise Exception(
                f"Error when creating InputOperator, '{input_node.id()}' was not an input node"
            )

        self.input_node: InputNode = input_node

    def id(self):
        return self.input_node.id()

    def returntype(self):
        out = first_value(self.input_node.outputs()).outtype

        if self.input_node is not None:
            import copy

            out = copy.copy(out)
            out.optional = False

        return out

    def __repr__(self):
        return "inputs." + self.input_node.id()

    def to_string_formatter(self):
        from janis_core.operators.stringformatter import StringFormatter

        key = self.input_node.id()
        kwarg = {key: self}
        return StringFormatter(f"{{{key}}}", **kwarg)


class StepOutputSelector(Selector):
    def __init__(self, node, tag):

        outputs = node.outputs()
        if tag not in outputs:
            raise TypeError(
                f"The step node {node.id()} did not have an output called '{tag}', "
                f"expected one of: {', '.join(outputs.keys())}"
            )

        self.node = node
        self.tag = tag

    def returntype(self):
        retval = self.node.outputs()[self.tag].outtype
        if self.node.scatter:
            retval = Array(retval)
        return retval

    @staticmethod
    def from_tuple(step_tuple):
        return StepOutputSelector(step_tuple[0], step_tuple[1])

    def __repr__(self):
        return self.node.id() + "." + self.tag

    def to_string_formatter(self):
        from janis_core.operators.stringformatter import StringFormatter

        key = self.node.id() + "_" + self.tag
        kwarg = {key: self}
        return StringFormatter(f"{{{key}}}", **kwarg)


class WildcardSelector(Selector):
    def __init__(self, wildcard):
        self.wildcard = wildcard

    def returntype(self):
        return Array(Union[File, Directory])

    def to_string_formatter(self):
        raise Exception("A wildcard selector cannot be coerced into a StringFormatter")


class MemorySelector(InputSelector):
    def __init__(self):
        super().__init__("runtime_memory")

    def returntype(self):
        return Int(optional=True)


class CpuSelector(InputSelector):
    def __init__(self, default=1):
        super().__init__("runtime_cpu")
        self.default = default

    def returntype(self):
        return Int(optional=bool(self.default is None))