"""
This class regenerates all the tool definitions

It's a bit of a random collection of things that should be refactored:

    - NestedDictionary (store values in nested structure (with root key))
    - RST Helpers
"""
from inspect import isfunction, ismodule, isabstract, isclass

from constants import PROJECT_ROOT_DIR
from janis.types.common_data_types import all_types, Array
from janis.types.data_types import DataType
from janis.workflow.workflow import Workflow

# Import modules here so that the tool registry knows about them

# Output settings
docs_dir = PROJECT_ROOT_DIR + "/docs/"
tools_dir = docs_dir + "tools/"
dt_dir = docs_dir + "datatypes/"

###### Shouldn't need to touch below this line #####

import os
from typing import List, Set, Type, Tuple

import tabulate
from datetime import date

from janis import CommandTool, Logger
from janis.tool.tool import Tool
from janis.utils.metadata import Metadata


class NestedDictionaryTypeException(Exception):
    def __init__(self, key, error_type, keys=None):
        keychain = (" for keys: " + ".".join(keys)) if keys else ""
        super(NestedDictionaryTypeException, self).__init__(
            f"Incorrect type '{error_type}' for key '{key}'{keychain}"
        )
        self.keys = keys
        self.key = key
        self.error_type = error_type


def format_rst_link(text, link):
    return f"`{text} <{link}>`_"


def prepare_tool(tool: Tool):
    # Stuff to list on the documentation page:
    #   - Versions of tools
    #   - Generated command
    #   - Cool if it grouped the tools by vendor
    #   -

    if not tool:
        return None

    # tool_modules = tool.__module__.split(".") # janis._bioinformatics_.tools.$toolproducer.$toolname.$version

    metadata = tool.metadata()
    if not tool.metadata():
        metadata = Metadata()

    fn = tool.friendly_name() if tool.friendly_name() else tool.id()
    en = f" ({tool.id()})" if fn != tool.id() else ""
    tn = fn + en

    formatted_url = (
        format_rst_link(metadata.documentationUrl, metadata.documentationUrl)
        if metadata.documentationUrl
        else "*No URL to the documentation was provided*"
    )

    input_headers = ["name", "type", "prefix", "position", "documentation"]

    required_input_tuples = [
        [i.id(), i.input_type.id(), i.prefix, i.position, i.doc]
        for i in tool.inputs()
        if not i.input_type.optional
    ]
    optional_input_tuples = [
        [i.id(), i.input_type.id(), i.prefix, i.position, i.doc]
        for i in tool.inputs()
        if i.input_type.optional
    ]

    formatted_required_inputs = tabulate.tabulate(
        required_input_tuples, input_headers, tablefmt="rst"
    )
    formatted_optional_inputs = tabulate.tabulate(
        optional_input_tuples, input_headers, tablefmt="rst"
    )

    output_headers = ["name", "type", "documentation"]
    output_tuples = [[o.id(), o.output_type.id(), o.doc] for o in tool.outputs()]
    formatted_outputs = tabulate.tabulate(output_tuples, output_headers, tablefmt="rst")

    docker_tag = ""
    if isinstance(tool, CommandTool):
        docker_tag = "Docker\n******\n``" + tool.docker() + "``\n"

    tool_prov = ""
    if tool.tool_provider() is None:
        print("Tool :" + tool.id() + " has no company")
    else:
        tool_prov = "." + tool.tool_provider().lower()

    return f"""
{fn}
{"=" * len(tn)}
Tool identifier: ``{tool.id()}``

Tool path: ``from janis_bioinformatics.tools{tool_prov} import {tool.__class__.__name__}``

Documentation
-------------

{docker_tag}
URL
******
{formatted_url}

Docstring
*********
{metadata.documentation if metadata.documentation else "*No documentation was provided: " + format_rst_link(
        "contribute one", "https://github.com/illusional") + "*"}

Outputs
-------
{formatted_outputs}

Inputs
------
Find the inputs below

Required inputs
***************

{formatted_required_inputs}

Optional inputs
***************

{formatted_optional_inputs}


Metadata
********

Author: {metadata.creator if metadata.creator else "**Unknown**"}


*{fn} was last updated on {metadata.dateUpdated if metadata.dateUpdated else "**Unknown**"}*.
*This page was automatically generated on {date.today().strftime("%Y-%m-%d")}*.
"""


def prepare_data_type(dt: DataType):
    dt_name = dt.name()
    secondary = ""

    if dt.secondary_files():
        secondary = "Secondary files: " + ", ".join(
            f"``{s}``" for s in dt.secondary_files()
        )

    return f"""
{dt_name}
{"=" * len(dt_name)}

{secondary}

Documentation
-------------

{dt.doc()}

*This page was automatically generated on {date.today().strftime("%Y-%m-%d")}*.
"""


def nested_keys_add(d, keys: List[str], value, root_key):
    if len(keys) == 0:
        if root_key in d:
            d[root_key].append(value)
        else:
            d[root_key] = [value]
        return d
    try:
        key = keys[0]
        if key in d:
            if not isinstance(d[key], dict):
                raise NestedDictionaryTypeException(
                    key=key, error_type=type(d[key]), keys=keys
                )
            nested_keys_add(d[key], keys[1:], value, root_key=root_key)
            return d
        else:
            d[key] = nested_keys_add({}, keys[1:], value, root_key=root_key)
    except NestedDictionaryTypeException as de:
        raise NestedDictionaryTypeException(
            key=de.key, error_type=de.error_type, keys=keys
        )

    return d


def get_toc(title, intro_text, subpages, caption="Contents", max_depth=1):
    prepared_subpages = "\n".join(
        "   " + m.lower() for m in sorted(subpages, key=lambda l: l.lower())
    )
    return f"""
{title.replace('{title}', title)}
{"=" * len(title)}

{intro_text}

.. toctree::
   :maxdepth: {max_depth}
   :caption: {caption}:

{prepared_subpages}

*This page was auto-generated on {date.today().strftime(
        "%d/%m/%Y")}. Please do not directly alter the contents of this page.*
"""


def get_tools_and_datatypes():
    import janis.bioinformatics, janis.unix

    modules = [janis.bioinformatics, janis.unix]

    tools: Set[Type[Tool]] = set()
    data_types: Set[Type[DataType]] = set(all_types)

    for m in modules:
        # noinspection PyTypeChecker
        tt, dt = get_tool_from_module(m.tools)
        # noinspection PyTypeChecker
        tdt, ddt = get_tool_from_module(m.data_types)

        tools = tools.union(tt).union(tdt)
        data_types = data_types.union(dt).union(ddt)

    return list(tools), list(data_types)


def get_tool_from_module(
    module, seen_modules=None
) -> Tuple[Set[Type[Tool]], Set[Type[DataType]]]:
    q = {
        n: cls
        for n, cls in list(module.__dict__.items())
        if not n.startswith("__") and type(cls) != type
    }

    tools: Set[Type[Tool]] = set()
    data_types: Set[Type[DataType]] = set()

    if seen_modules is None:
        seen_modules = set()

    for k in q:
        cls = q[k]
        try:
            if hasattr(cls, "__name__"):
                if cls.__name__ in seen_modules:
                    continue
                seen_modules.add(cls.__name__)

            if isfunction(cls):
                continue
            if ismodule(cls):
                t, d = get_tool_from_module(cls, seen_modules)
                tools = tools.union(t)
                data_types = data_types.union(d)
            elif isabstract(cls):
                continue
            elif not isclass(cls):
                continue
            elif issubclass(cls, CommandTool):
                print("Found commandtool: " + cls.tool())
                tools.add(cls)
            elif issubclass(cls, Workflow):
                print("Found workflow: " + cls().id())
                tools.add(cls)
            elif issubclass(cls, DataType):
                print("Found datatype: " + cls().id())
                data_types.add(cls)
        except Exception as e:
            print(f"{str(e)} for type {type(cls)}")
            # print(traceback.format_exc())
            continue

    return tools, data_types


def prepare_all_tools():
    tools, data_types = get_tools_and_datatypes()

    Logger.info(f"Preparing documentation for {len(tools)} tools")
    Logger.info(f"Preparing documentation for {len(data_types)} data_types")

    tool_module_index = {}
    dt_module_index = {}
    ROOT_KEY = "root"

    for t in tools:
        # tool = tool_vs[0][0]()
        tool = t()
        Logger.log("Preparing " + tool.id())
        output_str = prepare_tool(tool)

        tool_path_components = list(
            filter(lambda a: bool(a), [tool.tool_module(), tool.tool_provider()])
        )

        path_components = "/".join(tool_path_components)
        output_dir = f"{tools_dir}/{path_components}/".lower()
        output_filename = (output_dir + tool.id() + ".rst").lower()

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        nested_keys_add(
            tool_module_index, tool_path_components, tool.id(), root_key=ROOT_KEY
        )

        with open(output_filename, "w+") as tool_file:
            tool_file.write(output_str)

        Logger.log("Prepared " + tool.id())

    for d in data_types:
        # tool = tool_vs[0][0]()
        if issubclass(d, Array):
            Logger.info("Skipping Array DataType")
            continue

        dt = d()
        did = dt.name().lower()
        Logger.log("Preparing " + dt.name())
        output_str = prepare_data_type(dt)

        dt_path_components = []
        # dt_path_components = list(filter(
        #     lambda a: bool(a),
        #     [, tool.tool_provider()]
        # ))

        path_components = "/".join(dt_path_components)
        output_dir = f"{dt_dir}{path_components}/"
        output_filename = output_dir + did + ".rst"

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        nested_keys_add(dt_module_index, dt_path_components, did, root_key=ROOT_KEY)

        with open(output_filename, "w+") as dt_file:
            dt_file.write(output_str)

        Logger.log("Prepared " + did)

    def prepare_modules_in_index(contents, title, dir, max_depth=1):
        module_filename = dir + "/index.rst"
        module_tools = sorted(set(contents[ROOT_KEY] if ROOT_KEY in contents else []))
        submodule_keys = sorted(m for m in contents.keys() if m != ROOT_KEY)
        indexed_submodules_tools = [m.lower() + "/index" for m in submodule_keys]

        with open(module_filename, "w+") as module_file:
            module_file.write(
                get_toc(
                    title=title,
                    intro_text="Automatically generated index page for {title}",
                    subpages=indexed_submodules_tools + module_tools,
                    max_depth=max_depth,
                )
            )

        for submodule in submodule_keys:
            prepare_modules_in_index(
                contents=contents[submodule], title=submodule, dir=f"{dir}/{submodule}/"
            )

    prepare_modules_in_index(tool_module_index, title="Tools", dir=tools_dir)
    prepare_modules_in_index(
        dt_module_index, title="Data Types", dir=dt_dir, max_depth=1
    )


prepare_all_tools()
