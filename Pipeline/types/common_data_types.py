###################
# Implementations #
###################
from typing import Dict, Any

from Pipeline.utils.logger import Logger
from Pipeline.translations.cwl.cwl import Cwl
from Pipeline.types.data_types import DataType, NativeTypes, NativeType
from Pipeline.types.registry import register_type


class String(DataType):

    @staticmethod
    def name():
        return "String"

    @staticmethod
    def primitive():
        return NativeTypes.kStr

    @staticmethod
    def doc():
        return "A string"

    @classmethod
    def schema(cls) -> Dict:
        return {"type": "string", "required": True}

    def input_field_from_input(self, meta):
        return next(iter(meta.values()))

    def can_receive_from(self, other):
        if isinstance(other, Filename):
            return True
        return super().can_receive_from(other)


class Filename(String):

    def __init__(self, extension: str=None):
        """
        :param extension: with no '.' (dot)
        """
        super().__init__(optional=True)
        self.extension = extension

    @staticmethod
    def name() -> str:
        return "Filename"

    @staticmethod
    def primitive() -> NativeType:
        return NativeTypes.kStr

    @staticmethod
    def doc() -> str:
        return """
This class is a placeholder for generated filenames, by default it is optional and CAN be overrided, 
however the program has been structured in a way such that these names will be generated based on the step label. 
These should only be used when the tool _requires_ a filename to output and you aren't 
concerned what the filename should be. The Filename DataType should NOT be used as an output.
""".strip()

    @classmethod
    def schema(cls) -> Dict:
        pass

    def cwl(self) -> Dict[str, Any]:
        return {
            **super().cwl(),
            Cwl.CommandLineTool.Inputs.kDEFAULT: self.generated_filename()
        }

    def generated_filename(self, prefix: str=None) -> str:
        import uuid
        pre = (prefix + "-") if prefix is not None else ""
        ex = "" if self.extension is None else self.extension
        return pre + "generated-" + str(uuid.uuid1()) + ex

    def default(self) -> str:
        return self.generated_filename()

    def can_receive_from(self, other: DataType):
        # Specific override because Filename should be able to receive from string
        if isinstance(other, String):
            return True  # Always provides default, and is always optional
        return super().can_receive_from(other)


class Int(DataType):

    @staticmethod
    def name():
        return "Integer"

    @staticmethod
    def primitive():
        return NativeTypes.kInt

    @staticmethod
    def doc():
        return "An integer"

    @classmethod
    def schema(cls) -> Dict:
        return {"type": "number", "required": True}

    def input_field_from_input(self, meta):
        return next(iter(meta.values()))

class Float(DataType):

    @staticmethod
    def name():
        return "Float"

    @staticmethod
    def primitive():
        return NativeTypes.kFloat

    @staticmethod
    def doc():
        return "A float"

    @classmethod
    def schema(cls) -> Dict:
        return {"type": "number", "required": True}

    def input_field_from_input(self, meta):
        return next(iter(meta.values()))

class Double(DataType):

    @staticmethod
    def name():
        return "Double"

    @staticmethod
    def primitive():
        return NativeTypes.kDouble

    @staticmethod
    def doc():
        return "An integer"

    @classmethod
    def schema(cls) -> Dict:
        return {"type": "number", "required": True}

    def input_field_from_input(self, meta):
        return next(iter(meta.values()))


class Boolean(DataType):

    @staticmethod
    def name():
        return "Boolean"

    @staticmethod
    def primitive():
        return NativeTypes.kBool

    @staticmethod
    def doc():
        return "A boolean"

    @classmethod
    def schema(cls) -> Dict:
        return {"type": "boolean", "required": True}

    def input_field_from_input(self, meta):
        return next(iter(meta.values()))

    # def cwl(self) -> Dict[str, Any]:
        # return {
        #     **super().cwl(),
        #     "type": "Boolean",
        # }


class File(DataType):

    @staticmethod
    def name():
        return "File"

    @staticmethod
    def primitive():
        return NativeTypes.kFile

    @staticmethod
    def doc():
        return "A local file"

    @classmethod
    def schema(cls) -> Dict:
        return {
            "path": {"type": "string", "required": True}
        }

    def get_value_from_meta(self, meta):
        return meta.get("path")

    @staticmethod
    def cwl_input(value: Any):
        return {
            "class": Cwl.Primitives.kFILE,
            "path": value
        }


class Directory(DataType):
    @staticmethod
    def name():
        return "Directory"

    @staticmethod
    def primitive():
        return NativeTypes.kDirectory

    @staticmethod
    def doc():
        return "A directory of files"

    def get_value_from_meta(self, meta):
        return meta["path"]

    @classmethod
    def schema(cls) -> Dict:
        return {
            "path": {"type": "string", "required": True}
        }

    def input_field_from_input(self, meta):
        return meta["path"]

    @staticmethod
    def cwl_input(value: Any):
        # WDL: "{workflowName}.label" = meta["path"}
        return {
            "class": Cwl.Primitives.kDIRECTORY,
            "path": value
        }


class Array(DataType):

    def __init__(self, t: DataType, optional=False):
        if not isinstance(t, DataType):
            raise Exception(f"Type t ({type(t)}) must be an instance of 'Type'")

        self.__t = t
        super().__init__(optional)

    def subtype(self):
        return self.__t

    @staticmethod
    def name():
        return "Array"


    @staticmethod
    def primitive():
        return NativeTypes.kArray

    def id(self):
        if self.__t is None:
            return super().id()
        t = self.__t
        typed = f"Array<{t.id()}>"
        if self.optional:
            return f"Optional<{typed}>"
        return typed

    @staticmethod
    def doc():
        return "An array"

    @classmethod
    def schema(cls) -> Dict:
        return {"type": "array"}

    def cwl(self) -> Dict[str, Any]:
        dtype = {
                "type": NativeTypes.map_to_cwl(NativeTypes.kArray),
                "items": NativeTypes.map_to_cwl(self.__t.primitive()) + self.__t._question_mark_if_optional()
        }
        ret_val = ["null", dtype] if self.optional else dtype
        return {
            Cwl.Workflow.Input.kTYPE: ret_val
        }

    def wdl(self):
        return f"{NativeTypes.map_to_wdl(self.primitive())}[{NativeTypes.map_to_wdl(self.__t.primitive())}]"

    def can_receive_from(self, other):
        if isinstance(other, Array):
            return self.__t.can_receive_from(other.__t)
        if not self.__t.can_receive_from(other):
            return False
        return super().can_receive_from(other)

    def input_field_from_input(self, meta):
        return next(iter(meta.values()))


register_type(String)
register_type(Int)
register_type(Float)
register_type(Double)
register_type(Boolean)
register_type(Array)
register_type(File)
register_type(Directory)