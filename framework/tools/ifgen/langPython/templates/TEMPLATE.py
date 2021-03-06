# -*- coding: utf-8 -*-
from __future__ import print_function
{#-
 #  Jinja2 template for generating Python interface Legato APIs.
 #  This file acts as a wrapper for cffi interop, exposing only Pythonic code to the user.
 #
 #  Note: Python comments apply to the generated code.  For example this template itself is not
 #  autogenerated, but the comment is copied verbatim into the generated file when the template is
 #  expanded.
 #
 #  Copyright (C) Sierra Wireless Inc.
 #}
{%- for comment in fileComments %}
{{comment|PyFormatHeaderComment}}
{%- endfor %}

from {{apiName}}_native import ffi, lib
from enum import Enum, IntEnum
from collections import namedtuple
import sys

# IntEnum allows it to be compared with liblegato.Result
class Result(IntEnum):
    LE_OK = 0
    LE_NOT_FOUND = -1
    LE_NOT_POSSIBLE = -2
    LE_OUT_OF_RANGE = -3
    LE_NO_MEMORY = -4
    LE_NOT_PERMITTED = -5
    LE_FAULT = -6
    LE_COMM_ERROR = -7
    LE_TIMEOUT = -8
    LE_OVERFLOW = -9
    LE_UNDERFLOW = -10
    LE_WOULD_BLOCK = -11
    LE_DEADLOCK = -12
    LE_FORMAT_ERROR = -13
    LE_DUPLICATE = -14
    LE_BAD_PARAMETER = -15
    LE_CLOSED = -16
    LE_BUSY = -17
    LE_UNSUPPORTED = -18
    LE_IO_ERROR = -19
    LE_NOT_IMPLEMENTED = -20
    LE_UNAVAILABLE = -21
    LE_TERMINATED = -22

{%- for definition in definitions %}
{{definition.comment|PyFormatHeaderComment}}
{% if definition.value is number %}
{{definition.name}} = {{definition.value}}
{%- else %}
{{definition.name}} = "{{definition.value}}"
{%- endif %}
{%- endfor %}

{%- for type in types %}
{% if type is ReferenceType and type is not HandlerReferenceType %}
{{type.comment|PyFormatHeaderComment}}
class {{type.name}}_ref:
    def __init__(self, new_ref):
        self.native_ref = new_ref

    def __repr__(self):
        return "{{type.name}}(%s)" % self.native_ref
{%- elif type is EnumType or type is BitMaskType %}
{{type.comment|PyFormatHeaderComment}}
class {{type.name}}(Enum):
    {%- for element in type.elements %}
    {{element.name}} = {{element.value}}
    {%- endfor %}
{%- elif type is HandlerType -%}
{#- No need for exposing the handler type. Handled below in functions #}
{%- endif %}
{%- endfor %}

_handler_reg_queue = []
_connected = False

{%- for function in functions %}


{{function.comment|PyFormatHeaderComment}}
{%- if function is not EventFunction %}

{{function.name}}ReturnTuple = namedtuple('{{function.name}}ReturnTuple','result
    {%- for parameter in function.parameters if parameter.direction == 2 %} {{parameter.name}}
{%- endfor %}')

def {{function.name}}(
{% set add_default = False %}
{%- for parameter in function.parameters %}{{parameter.name}}
    {#- If a parameter uses a default parameter, the following parameters must also use a default one #}
    {%- if parameter.direction == 2 or add_default %}=None
    {% set add_default = True %}
    {%- endif %}
    {%- if not loop.last %}, {% endif %}
{%- endfor %}):
    {% set add_default = False %}
    {%- for parameter in function.parameters %}
        {%- if parameter.direction == 2 %}
            {#- do only output parameters need to be converted to pointers? probably. #}
            {%- if parameter.apiType|FormatType == 'char*' %}
    {{parameter.name}}_ptr = ffi.new("char[]", {{parameter.name}} if {{parameter.name}} is not None else 256)
    {#- i.e. default to blank char[256] if no string or length provided #}
            {%- else %}
    {{parameter.name}}_ptr = ffi.new("{{parameter.apiType|FormatType}} *")
    if {{parameter.name}} is not None:
        {{parameter.name}}_ptr[0] = {{parameter.name}}
    {#- TODO does this work for all types? might need more complex conversion #}
            {%- endif %}
    {{parameter.name}} = {{parameter.name}}_ptr
        {%- elif parameter.direction == 1 %}
            {%- if "BitMask" in parameter.apiType|FormatType %}
            {#- The C function needs an integer #}
    {{parameter.name}} = {{parameter.name}}.value
            {%- endif %}
        {%- endif %}
    {%- endfor %}
    result = lib.{{apiName}}_{{function.name}}(
        {%- for parameter in function.parameters %}{{parameter.name}}
        {#- If it's an output char*, fill out the size parameter #}
        {%- if parameter.apiType|FormatType == 'char*' and parameter.direction == 2 %}, ffi.sizeof({{parameter.name}}) {%- endif -%}
        {%- if not loop.last %}, {% endif %}
        {%- endfor %})
    {#- Casting back to python types #}
    {%- for parameter in function.parameters if parameter.direction == 2 %}
    {{parameter|CDataToPython}}
    {%- endfor %}
    {%- if function.returnType|FormatType == 'le_result_t' %}
    result = Result(result)
    {%- elif function.returnType is EnumType %}
    result = {{function.returnType.name}}(result)
    {%- elif function.returnType is BasicType and function.returnType.name == 'bool' %}
    result = bool(result)
    {%- elif function.returnType is BasicType
             or function.returnType is ReferenceType
             or function.returnType == None %}
    # No convertion for returnType = {{function.returnType}}
    {%- else %}
    # Not sure how to convert returnType = {{function.returnType}}
    {%- endif %}
    return {{function.name}}ReturnTuple(result=result{%- for parameter in function.parameters if parameter.direction == 2 %}, {{parameter.name}}={{parameter.name}}{%- endfor %})





{%-else%}

{%- if function.name.startswith('Add') %}
'''
Example Usage
(context argument is optional)

@{{apiName}}.{{function.event|DecoratorNameForEvent}}({%- for parameter in function.parameters if parameter.name != 'handler' -%}
    {{parameter.name}}, {% endfor -%}
    context={'some_data':"foo"})
{#- take the event's parameters, find the one called 'handler', and loop through its parameters (which are what the callback function takes) #}
def my_func({%- for parameter in function.event|HandlerParamsForEvent -%}
        {{parameter.name}}, {% endfor -%}
        context):
    print(context['some_data'])

# Or instead of decorator, bind it explicitly:
{{apiName}}.{{function.name}}(
    {%- for parameter in function.parameters -%}
    {%- if parameter.name == 'handler'%}my_func{%else%}{{parameter.name}}{% endif %}, {% endfor -%}
    context={'some_data':"foo"})
'''
{# add function #}
def {{function.name}}(
    {%- for parameter in function.parameters %}{{parameter.name}}
    {%- if not loop.last %}, {% endif %}
    {%- endfor %}, context=None):
    if context is None:
        context = {}
    {#- pack handler function and any additional keyword arguments into a tuple #}
    context_tuple = (handler, context)
    {#- get a pointer to it #}
    context_ptr = ffi.new_handle(context_tuple)
    {#- keep the pointer alive to prevent dangling
        (in CFFI, the pointer is who 'owns' the memory it points to) #}
    _{{function.event.name}}_pointers[handler] = context_ptr
    {#- register handler using native Legato method
        note: the extern function below is what actually gets registered. #}
    {#- we hijack the contextPtr argument to store which Python function should be bound
        alongside user context data. #}
    ref = lib.{{apiName}}_{{function.name}}(
            {% for parameter in function.parameters -%}
            {%- if parameter.name == 'handler' -%} lib.{{apiName}}_{{function.event.name}}Py
            {%- else -%} {{parameter.name}}
            {%- endif %}, {% endfor -%}
            context_ptr
        )
    _{{function.event.name}}_refs[handler] = ref
    return ref

{# decorator #}
def {{function.event|DecoratorNameForEvent}}(
    {%- for parameter in function.parameters if parameter.name != 'handler' %}{{parameter.name}}
    {%- if not loop.last %}, {% endif %}
    {%- endfor %}context=None):
    def inner(func):
        reg_func = lambda: {{function.name}}(
    {%- for parameter in function.parameters  %}{%- if parameter.name == 'handler'%}func{%else%}{{parameter.name}}{% endif %}
    {%- if not loop.last %}, {% endif %}
    {%- endfor %}, context)
        if _connected:
            reg_func()
        else:
            _handler_reg_queue.append(reg_func)
        return func
    return inner

_{{function.event.name}}_pointers = {}
_{{function.event.name}}_refs = {}

{#- extern "Python" function, defined in the C header but implemented here. #}
{#- it receives callbacks, and forwards it to the correct function #}

@ffi.def_extern()
def {{apiName}}_{{function.event.name}}Py(
        {%- for parameter in function.event|HandlerParamsForEvent %}{{parameter.name}}
        ,
        {%- endfor %} context_ptr):
    func, context = ffi.from_handle(context_ptr)
    {%- for parameter in function.event|HandlerParamsForEvent %}
    {{parameter|CDataToPython}}
    {%- endfor %}
    if context:
        func({%- for parameter in function.event|HandlerParamsForEvent %}{{parameter.name}}
        ,
        {%- endfor %} context=context)
    else:
        func({%- for parameter in function.event|HandlerParamsForEvent %}{{parameter.name}}
            {%- if not loop.last %},{% endif %}
            {%- endfor -%})

{%-else %}
def {{function.name}}(handler):
    try:
        handler_ref = _{{function.event.name}}_refs.pop(handler)
        del _{{function.event.name}}_pointers[handler]
    except KeyError as e:
        print('Could not find handlerRef for unregistering function %s! Did you register it?' % handler.func_name,
                file=sys.stderr)
    else:
        lib.{{apiName}}_{{function.name}}(handler_ref)
{%- endif %}
{%- endif %}
{%- endfor %}

def set_ServiceInstanceName(name):
    global _ServiceInstanceNamePtr
    global _ServiceInstanceNameDblPtr
    _ServiceInstanceNamePtr = ffi.new('char[]', name)
    _ServiceInstanceNameDblPtr = ffi.new('char**', _ServiceInstanceNamePtr)
    lib.{{apiName}}_ServiceInstanceNamePtr = _ServiceInstanceNameDblPtr

def _on_connect():
    global _connected
    _connected = True
    for f in _handler_reg_queue:
        f()
    del _handler_reg_queue[:]

def ConnectService():
    if not lib.{{apiName}}_ServiceInstanceNamePtr:
        print('Warning! ServiceInstanceName isn\'t set for {{apiName}}!',
              'e.g. {{apiName}}.set_ServiceInstanceName("foo.bar.{{apiName}}")', file=sys.stderr)
        print('Trying ConnectService() anyway, but it may segfault.', file=sys.stderr)
    lib.{{apiName}}_ConnectService()
    _on_connect()

def DisconnectService():
    lib.{{apiName}}_DisconnectService()
    _connected = False

def TryConnectService():
    result = lib.{{apiName}}_TryConnectService()
    if result == Result.LE_OK:
        _on_connect()
    return result

{# TODO disconnect handlers #}
