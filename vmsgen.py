#!/usr/bin/env python

# Copyright 2016-2019 VMware, Inc.
# SPDX-License-Identifier: MIT

# pylint: disable=C0111, E1121, R0913, R0914, R0911, W0703, E1101, C0301, W0511,C0413
from __future__ import print_function
from six.moves import http_client

from vmware.vapi.lib.connect import get_requests_connector
from vmware.vapi.stdlib.client.factories import StubConfigurationFactory
from com.vmware.vapi.metadata import metamodel_client

import six
import sys
import os
import argparse
import collections
import timeit
import json
import threading
import re
import requests
import warnings
warnings.filterwarnings("ignore")
from vmware.vapi.lib.constants import SHOW_UNRELEASED_APIS
from vmware.vapi.core import ApplicationContext


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


'''
This script uses metamodel apis and rest navigation to generate openapi json files
for apis available on vcenter.
'''

GENERATE_UNIQUE_OP_IDS = False
GENERATE_METAMODEL = False
API_SERVER_HOST = '<vcenter>'
TAG_SEPARATOR = '/'

#Enable filtering of all unreleased APIs except tech-preview features listed below.
enable_filtering = False


class HttpErrorMap:
    """
        Builds  error_map which maps vapi errors to http status codes.
    """
    def __init__(self, component_svc):
        self.component_svc = component_svc
        self.error_api_map = {}
        self.error_rest_map = {'com.vmware.vapi.std.errors.already_exists': http_client.BAD_REQUEST,
                     'com.vmware.vapi.std.errors.already_in_desired_state': http_client.BAD_REQUEST,
                     'com.vmware.vapi.std.errors.feature_in_use': http_client.BAD_REQUEST,
                     'com.vmware.vapi.std.errors.internal_server_error': http_client.INTERNAL_SERVER_ERROR,
                     'com.vmware.vapi.std.errors.invalid_argument': http_client.BAD_REQUEST,
                     'com.vmware.vapi.std.errors.invalid_element_configuration': http_client.BAD_REQUEST,
                     'com.vmware.vapi.std.errors.invalid_element_type': http_client.BAD_REQUEST,
                     'com.vmware.vapi.std.errors.invalid_request': http_client.BAD_REQUEST,
                     'com.vmware.vapi.std.errors.not_found': http_client.NOT_FOUND,
                     'com.vmware.vapi.std.errors.operation_not_found': http_client.NOT_FOUND,
                     'com.vmware.vapi.std.errors.not_allowed_in_current_state': http_client.BAD_REQUEST,
                     'com.vmware.vapi.std.errors.resource_busy': http_client.BAD_REQUEST,
                     'com.vmware.vapi.std.errors.resource_in_use': http_client.BAD_REQUEST,
                     'com.vmware.vapi.std.errors.resource_inaccessible': http_client.BAD_REQUEST,
                     'com.vmware.vapi.std.errors.service_unavailable': http_client.SERVICE_UNAVAILABLE,
                     'com.vmware.vapi.std.errors.timed_out': http_client.GATEWAY_TIMEOUT,
                     'com.vmware.vapi.std.errors.unable_to_allocate_resource': http_client.BAD_REQUEST,
                     'com.vmware.vapi.std.errors.unauthenticated': http_client.UNAUTHORIZED,
                     'com.vmware.vapi.std.errors.unauthorized': http_client.FORBIDDEN,
                     'com.vmware.vapi.std.errors.unexpected_input': http_client.BAD_REQUEST,
                     'com.vmware.vapi.std.errors.unsupported': http_client.BAD_REQUEST,
                     'com.vmware.vapi.std.errors.error': http_client.BAD_REQUEST,
                     'com.vmware.vapi.std.errors.concurrent_change': http_client.BAD_REQUEST,
                     'com.vmware.vapi.std.errors.canceled': http_client.BAD_REQUEST,
                     'com.vmware.vapi.std.errors.unverified_peer': http_client.BAD_REQUEST}

        structures = self.component_svc.get('com.vmware.vapi').info.packages['com.vmware.vapi.std.errors'].structures
        for structure in structures:
            try:
                if structures[structure].metadata['Response'] is not None:
                    code = structures[structure].metadata['Response'].elements['code'].string_value
                    self.error_api_map[structure] = int(code)
            except KeyError:
                print(structure + " :: is does not have an Error Code")


def is_filtered(metadata):
    if not enable_filtering:
        return False
    if len(metadata) == 0:
        return False
    if 'TechPreview' in metadata:
        return False
    if 'Changing' in metadata or 'Proposed' in metadata:
        return True
    return False


def load_description():
    """
    Loads description.properties into a dictionary.
    """
    desc = {
        'content': 'VMware vSphere\u00ae Content Library empowers vSphere Admins to effectively manage VM templates, '
                   'vApps, ISO images and scripts with ease.', 'spbm': 'SPBM',
        'vapi': 'vAPI is an extensible API Platform for modelling and delivering APIs/SDKs/CLIs.',
        'vcenter': 'VMware vCenter Server provides a centralized platform for managing your VMware vSphere environments'
        , 'appliance': 'The vCenter Server Appliance is a preconfigured Linux-based virtual machine'
          ' optimized for running vCenter Server and associated services.'}
    return desc


def write_json_data_to_file(file_name, json_data):
    """
    Utility method used to write json file.
    """
    with open(file_name, 'w+') as outfile:
        json.dump(json_data, outfile, indent=4, sort_keys=True)


def get_json(url, verify=True):
    try:
        req = requests.get(url, verify=verify)
    except Exception as ex:
        eprint('Cannot Load %s - %s' % (url, req.content))
        eprint(ex)
        return None
    if not req.ok:
        eprint('Cannot Load %s - %s' % (url, req.content))
        return None
    if 'value' in req.json():
        return req.json()['value']
    return req.json()


def get_component_services_urls(cloudvm_url, verify=True):
    components_url = get_json(cloudvm_url, verify)['components']['href']
    components = get_json(components_url, verify)
    return [component['services']['href'] for component in components]


def get_all_services_urls(components_urls, verify=True):
    service_url_dict = {}
    for url in components_urls:
        services = get_json(url, verify)
        for service in services:
            service_url_dict[service['href']] = service['name']
    return service_url_dict


def get_service_info(service_id, service_dict):
    """
    Given a service_id, return its ServiceInfo
    """
    try:
        service_info = service_dict.get(service_id)
        return service_info
    except Exception as exception:
        eprint(exception)
        return None


def metamodel_to_swagger_type_converter(input_type):
    """
    Converts API Metamodel type to their equivalent Swagger type.
    A tuple is returned. first value of tuple is main type.
    second value of tuple has 'format' information, if available.
    """
    input_type = input_type.lower()
    if input_type == 'date_time':
        return 'string', 'date-time'
    if input_type == 'secret':
        return 'string', 'password'
    if input_type == 'any_error':
        return 'object', None
    if input_type == 'dynamic_structure':
        return 'object', None
    if input_type == 'uri':
        return 'string', 'uri'
    if input_type == 'id':
        return 'string', None
    if input_type == 'long':
        return 'integer', 'int64'
    if input_type == 'double':
        return 'number', 'double'
    if input_type == 'binary':
        return 'string', 'binary'
    return input_type, None


class typeHandler():

    def __init__(self, endpoint):
        self.endpoint = endpoint

    def visit_type_category(self, struct_type, new_prop, type_dict, structure_svc, enum_svc):
        if isinstance(struct_type, dict):
            return self.visit_type_category_dict(struct_type, new_prop, type_dict, structure_svc, enum_svc)
        if struct_type.category == 'BUILTIN':
            self.visit_builtin(struct_type.builtin_type, new_prop)
        elif struct_type.category == 'GENERIC':
            self.visit_generic(struct_type.generic_instantiation, new_prop, type_dict, structure_svc,
                        enum_svc)
        elif struct_type.category == 'USER_DEFINED':
            self.visit_user_defined(struct_type.user_defined_type, new_prop, type_dict, structure_svc,
                            enum_svc)

    def visit_type_category_dict(self, struct_type, new_prop, type_dict, structure_svc, enum_svc):
        new_prop['required'] = True
        if struct_type['category'] == 'BUILTIN':
            self.visit_builtin(struct_type['builtin_type'], new_prop)
        elif struct_type['category'] == 'GENERIC':
            self.visit_generic(struct_type['generic_instantiation'], new_prop, type_dict, structure_svc,
                        enum_svc)
        elif struct_type['category'] == 'USER_DEFINED':
            self.visit_user_defined(struct_type['user_defined_type'], new_prop, type_dict, structure_svc,
                            enum_svc)

    def visit_builtin(self, builtin_type, new_prop):
        data_type, format_ = metamodel_to_swagger_type_converter(builtin_type)
        if 'type' in new_prop and new_prop['type'] == 'array':
            item_obj = {'type': data_type}
            new_prop['items'] = item_obj
            if format_ is not None:
                item_obj['format'] = format_
        else:
            new_prop['type'] = data_type
            if format_ is not None:
                new_prop['format'] = format_

    def visit_generic(self, generic_instantiation, new_prop, type_dict, structure_svc, enum_svc):
        if generic_instantiation.generic_type == 'OPTIONAL':
            new_prop['required'] = False
            self.visit_type_category(generic_instantiation.element_type, new_prop, type_dict,
                                structure_svc, enum_svc)
        elif generic_instantiation.generic_type == 'LIST':
            new_prop['type'] = 'array'
            self.visit_type_category(generic_instantiation.element_type, new_prop, type_dict,
                                structure_svc, enum_svc)
        elif generic_instantiation.generic_type == 'SET':
            new_prop['type'] = 'array'
            new_prop['uniqueItems'] = True
            self.visit_type_category(generic_instantiation.element_type, new_prop, type_dict,
                                structure_svc, enum_svc)
        elif generic_instantiation.generic_type == 'MAP':
            # Have static key/value pair object maping for /rest paths
            # while use additionalProperties for /api paths
            if self.endpoint == "rest": 
                new_type = {'type': 'object', 'properties': {}}
            elif self.endpoint == "api":
                new_type = {'type': 'object', 'additionalProperties': {}}

            if self.endpoint == "rest":
                if generic_instantiation.map_key_type.category == 'USER_DEFINED':
                    res_id = generic_instantiation.map_key_type.user_defined_type.resource_id
                    res_type = generic_instantiation.map_key_type.user_defined_type.resource_type
                    
                    new_type['properties']['key'] = {'$ref': '#/definitions/' + res_id}
                    self.check_type(res_type, res_id, type_dict, structure_svc, enum_svc)
                else:
                    new_type['properties']['key'] = {'type': metamodel_to_swagger_type_converter(
                        generic_instantiation.map_key_type.builtin_type)[0]}

            if generic_instantiation.map_value_type.category == 'USER_DEFINED':
                
                if self.endpoint == "rest":
                    new_type['properties']['value'] = {
                        '$ref': '#/definitions/' + generic_instantiation.map_value_type.user_defined_type.resource_id}
                elif self.endpoint == "api":
                    new_type['additionalProperties'] = {
                        '$ref': '#/definitions/' + generic_instantiation.map_value_type.user_defined_type.resource_id
                    }

                res_type = generic_instantiation.map_value_type.user_defined_type.resource_type
                res_id = generic_instantiation.map_value_type.user_defined_type.resource_id
                self.check_type(res_type, res_id, type_dict, structure_svc, enum_svc)

            elif generic_instantiation.map_value_type.category == 'BUILTIN':
                if self.endpoint == "rest":
                    new_type['properties']['value'] = {'type': metamodel_to_swagger_type_converter(
                    generic_instantiation.map_value_type.builtin_type)[0]}
                elif self.endpoint == "api":
                    new_type['additionalProperties'] = {'type': metamodel_to_swagger_type_converter(
                    generic_instantiation.map_value_type.builtin_type)[0]}

            elif generic_instantiation.map_value_type.category == 'GENERIC':
                temp_new_type = {}
                self.visit_generic( generic_instantiation.map_value_type.generic_instantiation,
                            temp_new_type, type_dict, structure_svc, enum_svc)
                
                if self.endpoint == "rest":
                    new_type['properties']['value'] = temp_new_type
                elif self.endpoint == "api":
                    new_type['additionalProperties'] = temp_new_type
                
            if self.endpoint == "rest":
                new_prop['type'] = 'array'
                new_prop['items'] = new_type
            elif self.endpoint == "api":
                new_prop.update(new_type)

            if 'additionalProperties' in new_type:
                if not new_type['additionalProperties'].get('required', True):
                    del new_type['additionalProperties']['required']

            if '$ref' in new_prop:
                del new_prop['$ref']

    def is_type_builtin(self, type_):
        type_ = type_.lower()
        typeset = {'binary', 'boolean', 'datetime', 'double', 'dynamicstructure', 'exception',
                'id', 'long', 'opaque', 'secret', 'string', 'uri'}
        if type_ in typeset:
            return True
        return False

    def get_structure_info(self, struct_type, structure_svc):
        """
        Given a type, return its structure info, if the type is a structure.
        """
        try:
            structure_info = structure_svc.get(struct_type)
            if structure_info is None:
                eprint("Could not fetch structure info for " + struct_type)
            elif is_filtered(structure_info.metadata):
                return None
            else:
                structure_info.fields = [field for field in structure_info.fields if not is_filtered(field.metadata)]
                return structure_info
        except Exception as ex:
            eprint("Error fetching structure info for " + struct_type)
            eprint(ex)
            return None

    def process_structure_info(self, type_name, structure_info, type_dict, structure_svc, enum_svc):
        new_type = {'type': 'object', 'properties': {}}
        for field in structure_info.fields:
            newprop = {'description': field.documentation}
            if field.type.category == 'BUILTIN':
                self.visit_builtin(field.type.builtin_type, newprop)
            elif field.type.category == 'GENERIC':
                self.visit_generic(field.type.generic_instantiation, newprop, type_dict,
                            structure_svc, enum_svc)
            elif field.type.category == 'USER_DEFINED':
                self.visit_user_defined(field.type.user_defined_type, newprop, type_dict,
                                structure_svc, enum_svc)
            new_type['properties'].setdefault(field.name, newprop)
        required = []
        for property_name, property_value in six.iteritems(new_type['properties']):
            if 'required' not in property_value:
                required.append(property_name)
            elif property_value['required'] == 'true':
                required.append(property_name)
        if len(required) > 0:
            new_type['required'] = required
        type_dict[type_name] = new_type

    def get_enum_info(self, type_name, enum_svc):
        """
        Given a type, return its enum info, if the type is enum.
        """
        try:
            enum_info = enum_svc.get(type_name)
            if enum_info is None:
                eprint("Could not fetch enum info for " + type_name)
            elif is_filtered(enum_info.metadata):
                return None
            else:
                return enum_info
        except Exception as exception:
            eprint("Error fetching enum info for " + type_name)
            eprint(exception)
            return None

    def process_enum_info(self, type_name, enum_info, type_dict):
        enum_type = {'type': 'string', 'description': enum_info.documentation}
        enum_type.setdefault('enum', [value.value for value in enum_info.values if not is_filtered(value.metadata)])
        type_dict[type_name] = enum_type

    def check_type(self, resource_type, type_name, type_dict, structure_svc, enum_svc):
        if type_name in type_dict or self.is_type_builtin(type_name):
            return
        if resource_type == 'com.vmware.vapi.structure':
            structure_info = self.get_structure_info(type_name, structure_svc)
            if structure_info is not None:
                # Mark it as visited to handle recursive definitions. (Type A referring to Type A in one of the fields).
                type_dict[type_name] = {}
                self.process_structure_info(type_name, structure_info, type_dict, structure_svc, enum_svc)
        else:
            enum_info = self.get_enum_info(type_name, enum_svc)
            if enum_info is not None:
                # Mark it as visited to handle recursive definitions. (Type A referring to Type A in one of the fields).
                type_dict[type_name] = {}
                self.process_enum_info(type_name, enum_info, type_dict)

    def visit_user_defined(self, user_defined_type, newprop, type_dict, structure_svc, enum_svc):
        if user_defined_type.resource_id is None:
            return
        if 'type' in newprop and newprop['type'] == 'array':
            item_obj = {'$ref': '#/definitions/' + user_defined_type.resource_id}
            newprop['items'] = item_obj
        # if not array, fill in type or ref
        else:
            newprop['$ref'] = '#/definitions/' + user_defined_type.resource_id

        self.check_type(user_defined_type.resource_type, user_defined_type.resource_id, type_dict, structure_svc, enum_svc)


def find_string_element_value(element_value):
    """
    if input parameter is a path variable, this method
    determines name of the path variable.
    """
    if element_value is dict:
        if element_value['type'] == 'STRING':
            return element_value['string_value']
    else:
        return element_value.string_value


def convert_field_info_to_swagger_parameter(param_type, input_parameter_obj, type_dict,
                                            structure_svc, enum_svc, endpoint):
    """
    Converts metamodel fieldinfo to swagger parameter.
    """
    parameter_obj = {}
    tpHandler = typeHandler(endpoint)
    tpHandler.visit_type_category(input_parameter_obj.type, parameter_obj, type_dict, structure_svc, enum_svc)
    if 'required' not in parameter_obj:
        parameter_obj['required'] = True
    parameter_obj['in'] = param_type
    parameter_obj['name'] = input_parameter_obj.name
    parameter_obj['description'] = input_parameter_obj.documentation
    # $ref should be encapsulated in 'schema' instead of parameter. -> this throws swagger validation error
    # hence another method is to to get data in $ref in parameter_obj itself
    if '$ref' in parameter_obj:
        type_obj = type_dict[parameter_obj['$ref'][len("#/definitions/"):]]
        description = parameter_obj['description']
        if 'description' in type_obj:
            description = ""
            description = "{ 1. " + type_obj['description'] + " }, { 2. " + parameter_obj['description'] + " }"
        parameter_obj.update(type_obj)
        parameter_obj['description'] = description
        del parameter_obj['$ref']
    return parameter_obj


def get_response_object_name(service_id, operation_id):
    if operation_id == 'get':
        return service_id
    return service_id + '.' + operation_id


def populate_response_map(output, errors, http_error_map, type_dict, structure_svc, enum_svc, op_metadata, service_name, operation_id, endpoint):

    response_map = {}
    schema = {}
    success_response = {'description': output.documentation}
    tpHandler = typeHandler(endpoint)
    tpHandler.visit_type_category(output.type, schema, type_dict, structure_svc, enum_svc)
    # if type of schema is void, don't include it.
    # this prevents showing response as void in swagger-ui
    if schema is not None:
        if not ('type' in schema and schema['type'] == 'void'):
            # Handling Value wrappers for /rest and /api
            if endpoint == "rest":
                value_wrapper = {
                    'type': 'object',
                    'properties': {'value': schema},
                    'required': ['value']
                }
                type_name = get_response_object_name(service_name, operation_id) + '_resp'
                if type_name not in type_dict.keys():
                    type_dict[type_name] = value_wrapper
                resp = {"$ref": "#/definitions/" + type_name}
            elif endpoint == "api":
                resp = schema
            else:
                print("Endpoint at populate_response_map is unknown : ", endpoint)

            success_response['schema'] = resp

    success_response_code = requests.codes.ok
    if endpoint == 'api' and 'Response' in op_metadata and op_metadata['Response'] is not None:
        success_response_code = int(op_metadata['Response'].elements['code'].string_value)
    # success response is not mapped through metamodel.
    # hardcode it for now apis under /rest.
    response_map[success_response_code] = success_response

    for error in errors:
        tpHandler.check_type('com.vmware.vapi.structure', error.structure_id, type_dict, structure_svc, enum_svc)
        if endpoint == "rest":
            status_code = http_error_map.error_rest_map.get(error.structure_id, http_client.INTERNAL_SERVER_ERROR)
            schema_obj = {'type': 'object', 'properties': {'type': {'type': 'string'},
                                                        'value': {'$ref': '#/definitions/' + error.structure_id}}}
            type_dict[error.structure_id + '_error'] = schema_obj
            response_obj = {'description': error.documentation, 'schema': {'$ref': '#/definitions/'
                                                                               + error.structure_id + '_error'}}
        elif endpoint == "api":
            status_code = http_error_map.error_api_map.get(error.structure_id, http_client.INTERNAL_SERVER_ERROR)
            response_obj = {'description': error.documentation, 'schema': {'$ref': '#/definitions/'
                                                                               + error.structure_id}}

        response_map[status_code] = response_obj
    return response_map


def post_process_path(path_obj):
    # Temporary fixes necessary for generated spec files.
    # Hardcoding for now as it is not available from metadata.
    if path_obj['path'] == '/com/vmware/cis/session' and path_obj['method'] == 'post':
        header_parameter = {'in': 'header', 'required': True, 'type': 'string',
                            'name': 'vmware-use-header-authn',
                            'description': 'Custom header to protect against CSRF attacks in browser based clients'}
        path_obj['parameters'] = [header_parameter]

    # Allow invoking $task operations from the api-explorer
    if path_obj['operationId'].endswith('$task'):
        path_obj['path'] = add_query_param(path_obj['path'], 'vmw-task=true')


def add_query_param(url, param):
    """
    Rudimentary support for adding a query parameter to a url.
    Does nothing if the parameter is already there.
    :param url: the input url
    :param param: the parameter to add (in the form of key=value)
    :return: url with added param, ?param or &param at the end
    """
    pre_param_symbol = '?'
    query_index = url.find('?')
    if query_index > -1:
        if query_index == len(url):
            pre_param_symbol = ''
        elif url[query_index + 1:].find(param) > -1:
            return url
        else:
            pre_param_symbol = '&'
    return url + pre_param_symbol + param


def add_basic_auth(path_obj):
    """Add basic auth security requirement to paths requiring it."""
    if path_obj['path'] == '/com/vmware/cis/session' and path_obj['method'] == 'post':
        path_obj['security'] = [{'basic_auth': []}]


def tags_from_service_name(service_name):
    """
    Generates the tags based on the service name.
    :param service_name: name of the service
    :return: a list of tags
    """
    global TAG_SEPARATOR
    return [TAG_SEPARATOR.join(service_name.split('.')[3:])]


def build_path(service_name, method, path, documentation, parameters, operation_id, responses, consumes,
               produces):
    """
    builds swagger path object
    :param service_name: name of service. ex com.vmware.vcenter.VM
    :param method: type of method. ex put, post, get, patch
    :param path: relative path to an individual endpoint
    :param documentation: api documentation
    :param parameters: input parameters for the api
    :param responses: response of the api
    :param consumes: expected media type format of api input
    :param produces: expected media type format of api output
    :return: swagger path object.
    """
    path_obj = {}
    path_obj['tags'] = tags_from_service_name(service_name)
    if method is not None:
        path_obj['method'] = method
    if path is not None:
        path_obj['path'] = path
    if documentation is not None:
        path_obj['summary'] = documentation
    if parameters is not None:
        path_obj['parameters'] = parameters
    if responses is not None:
        path_obj['responses'] = responses
    if consumes is not None:
        path_obj['consumes'] = consumes
    if produces is not None:
        path_obj['produces'] = produces
    if operation_id is not None:
        path_obj['operationId'] = operation_id
    post_process_path(path_obj)
    add_basic_auth(path_obj)
    return path_obj


def convert_path_list_to_path_map(path_list):
    """
    The same path can have multiple methods.
    For example: /vcenter/vm can have 'get', 'patch', 'put'
    Rearrange list into a map/object which is the format expected by swagger-ui
    key is the path ie. /vcenter/vm/
    value is a an object which contains key as method names and value as path objects
    """
    path_dict = {}
    for path in path_list:
        x = path_dict.get(path['path'])
        if x is None:
            x = {path['method']: path}
            path_dict[path['path']] = x
        else:
            x[path['method']] = path
    return path_dict


def cleanup(path_dict, type_dict):
    for _, type_object in six.iteritems(type_dict):
        if 'properties' in type_object or 'additionalProperties' in type_object:

            if 'properties' in type_object:
                properties = type_object['properties']
            else:
                properties = type_object['additionalProperties']

            for key, property_value in properties.items():
                if isinstance(property_value, dict):
                    if 'required' in property_value and isinstance(property_value['required'], bool):
                        del property_value['required']
                        
    for _, path_value in six.iteritems(path_dict):
        for _, method_value in six.iteritems(path_value):
            if 'path' in method_value:
                del method_value['path']
            if 'method' in method_value:
                del method_value['method']


def remove_com_vmware_from_dict(swagger_obj, depth=0, keys_list=[]):
    """
    The method
    1. removes 'com.vmware.' from model names
    2. replaces $ with _ from the model names

    This is done on both definitions and path
    'definitions' : where models are defined and may be referenced.
    'path' : where models are referenced.
    :param swagger_obj: should be path of definitions dictionary
    :param depth: depth of the dictionary. Defaults to 0
    :param keys_list: List of updated model names
    :return:
    """
    if isinstance(swagger_obj, dict):
        if '$ref' in swagger_obj and 'required' in swagger_obj:
            del swagger_obj['required']
        for key, item in swagger_obj.items():
            if isinstance(item, str):
                if key in ('$ref', 'summary', 'description'):
                    item = item.replace('com.vmware.', '')
                    if key == '$ref':
                        item = item.replace('$', '_')
                    swagger_obj[key] = item
            elif isinstance(item, list):
                for itm in item:
                    remove_com_vmware_from_dict(itm, depth+1, keys_list)
            elif isinstance(item, dict):
                if depth == 0 and isinstance(key, str) and (key.startswith('com.vmware.') or '$' in key):
                    keys_list.append(key)
                remove_com_vmware_from_dict(item, depth+1, keys_list)
    elif isinstance(swagger_obj, list):
        for itm in swagger_obj:
            remove_com_vmware_from_dict(itm, depth+1)
    if depth == 0 and len(keys_list) > 0:
        while keys_list:
            old_key = keys_list.pop()
            new_key = old_key.replace('com.vmware.', '')
            new_key = new_key.replace('$', '_')
            try:
                swagger_obj[new_key] = swagger_obj.pop(old_key)
            except KeyError:
                print('Could not find the Swagger Element :  {}'.format(old_key))


def create_camelized_op_id(path, http_method, operations_dict):
    """
    Creates camelized operation id.
    Takes the path, http_method and operation dictionary as input parameter:
    1. Iterates through all the operation array to return the current operation id
    2. Appends path to the existing operation id and
     replaces '/' and '-' with '_' and removes 'com_vmware_'
    3. Splits the string by '_'
    4. Converts the first letter of all the words except the first one from lower to upper
    5. Joins all the words together and returns the new camelcase string

    e.g
        parameter : abc_def_ghi
        return    : AbcDefGhi
    :param path:
    :param http_method:
    :param operations_dict:
    :return: new_op_id
    """
    curr_op_id = operations_dict['operationId']
    raw_op_id = curr_op_id.replace('-', '_')
    new_op_id = raw_op_id
    if '_' in raw_op_id:
        raw_op_id_iter = iter(raw_op_id.split('_'))
        new_op_id = next(raw_op_id_iter)
        for new_op_id_element in raw_op_id_iter:
            new_op_id += new_op_id_element.title()
    ''' 
        Removes query parameters form the path. 
        Only path elements are used in operation ids
    '''
    paths_array = re.split('\?', path)
    path = paths_array[0]
    path_elements = path.replace('-', '_').split('/')
    path_elements_iter = iter(path_elements)
    for path_element in path_elements_iter:
        if '{' in path_element:
            continue
        if 'com' == path_element or 'vmware' == path_element:
            continue
        if path_element.lower() == raw_op_id.lower():
            continue
        if '_' in path_element:
            sub_path_iter = iter(path_element.split('_'))
            for sub_path_element in sub_path_iter:
                new_op_id += sub_path_element.title()
        else:
            new_op_id += path_element.title()
    return new_op_id


def create_unique_op_ids(path_dict):
    """
    Creates unique operation ids
    Takes the path dictionary as input parameter:
    1. Iterates through all the http_operation array
    2. For every operation gets the current operation id
    3. Calls method to get the camelized operation id
    4. Checks for uniqueness
    5. Updates the path dictionary with the unique operation id
    
    :param path_dict:
    """
    op_id_list = ['get', 'set', 'list', 'add', 'run', 'start', 'stop',
                  'restart', 'reset', 'cancel', 'create', 'update', 'delete']
    for path, http_operation in path_dict.items():
        for http_method, operation_dict in http_operation.items():
            op_id_val = create_camelized_op_id(path, http_method, operation_dict)
            if op_id_val not in op_id_list:
                operation_dict['operationId'] = op_id_val
                op_id_list.append(op_id_val)


def merge_dictionaries(x, y):
    z = x.copy()   # start with x's keys and values
    z.update(y)    # modifies z with y's keys and values & returns None
    return z


def remove_query_params(path_dict):
    """
    Swagger/Open API specification prohibits appending query parameter to the request mapping path.

    Duplicate paths in Open API :
        Since request mapping paths are keys in the Open Api JSON, there is no scope of duplicate request mapping paths

    Partial Duplicates in Open API: APIs which have same request mapping paths but different HTTP Operations.

    Such Operations can be merged together under one path
        eg: Consider these two paths
            /A/B/C : [POST]
            /A/B/C : [PUT]
        On merging these, the new path would look like:
        /A/B/C : [POST, PUT]

    Absolute Duplicates in Open API: APIs which have same request mapping path and HTTP Operation(s)
        eg: Consider two paths
            /A/B/C : [POST, PUT]
            /A/B/C : [PUT]
    Such paths can not co-exist in the same Open API definition.

    This method attempts to move query parameters from request mapping url to parameter section.

    There are 4 possibilities which may arise on removing the query parameter from request mapping path:

     1. Absolute Duplicate
        The combination of path and the HTTP Operation Type(s)are same to that of an existing path:
        Handling Such APIs is Out of Scope of this method. Such APIs will appear in the Open API definition unchanged.
        Example :
                /com/vmware/cis/session?~action=get : [POST]
                /com/vmware/cis/session : [POST, DELETE]
    2. Partial Duplicate:
        The Paths are same but the HTTP operations are Unique:
        Handling Such APIs involves adding the Operations of the new duplicate path to that of the existing path
        Example :
                /cis/tasks/{task}?action=cancel : [POST]
                /cis/tasks/{task} : [GET]
    3. New Unique Path:
        The new path is not a duplicate of any path in the current Open API definition.
        The Path is changed to new path by trimming off the path post '?'

    4. The duplicate paths are formed when two paths with QueryParameters are fixed
        All the scenarios under 1, 2 and 3 are possible.
        Example :
                /com/vmware/cis/tagging/tag-association/id:{tag_id}?~action=detach-tag-from-multiple-objects
                /com/vmware/cis/tagging/tag-association/id:{tag_id}?~action=list-attached-objects
    :param path_dict:
    """
    paths_to_delete = []
    for old_path, http_operations in path_dict.items():
        if '?' in old_path:
            paths_array = re.split('\?', old_path)
            new_path = paths_array[0]

            query_param = []
            for query_parameter in paths_array[1].split('&'):
                key_value = query_parameter.split('=')
                q_param = {'name': key_value[0], 'in': 'query', 'description': key_value[0] + '=' + key_value[1],
                        'required': True, 'type': 'string', 'enum': [key_value[1]]}
                query_param.append(q_param)

            if new_path in path_dict:
                new_path_operations = path_dict[new_path].keys()
                path_operations = http_operations.keys()
                if len(set(path_operations).intersection(new_path_operations)) < 1:
                    for http_method, operation_dict in http_operations.items():
                        operation_dict['parameters'] = operation_dict['parameters'] + query_param
                    path_dict[new_path] = merge_dictionaries(http_operations, path_dict[new_path])
                    paths_to_delete.append(old_path)
            else:
                for http_method, operation_dict in http_operations.items():
                    operation_dict['parameters'].append(q_param)
                path_dict[new_path] = path_dict.pop(old_path)
    for path in paths_to_delete:
        del path_dict[path]


def process_output(path_dict, type_dict, output_dir, output_filename):
    description_map = load_description()
    remove_com_vmware_from_dict(path_dict)
    global GENERATE_UNIQUE_OP_IDS
    if GENERATE_UNIQUE_OP_IDS:
        create_unique_op_ids(path_dict)
    remove_query_params(path_dict)
    remove_com_vmware_from_dict(type_dict)
    swagger_template = {'swagger': '2.0',
                        'info': {'description': description_map.get(output_filename, ''),
                                 'title': output_filename,
                                 'termsOfService': 'http://swagger.io/terms/',
                                 'version': '2.0.0'},
                        'host': API_SERVER_HOST,
                        'securityDefinitions': {
                            'basic_auth': {'type': 'basic'},
                            'api_key': {'type': 'apiKey', 'name': 'vmware-api-session-id', 'in': 'header'}},
                        "security": [{"api_key": []}],
                        'consumes': ['application/json'],
                        'produces': ['application/json'],
                        'basePath': '', 'tags': [],
                        'schemes': ['https', 'http'],
                        'paths': collections.OrderedDict(sorted(path_dict.items())),
                        'definitions': collections.OrderedDict(sorted(type_dict.items()))}
    
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    write_json_data_to_file(output_dir + os.path.sep + output_filename + '.json', swagger_template)


def find_consumes(method_type):
    """
    Determine mediaType for input parameters in request body.
    """
    if method_type in ('get', 'delete'):
        return None
    return ['application/json']


def extract_body_parameters(params):
    body_params = []
    other_params = []
    for param in params:
        if 'Body' in param.metadata:
            body_params.append(param)
        else:
            other_params.append(param)
    return body_params, other_params


def extract_query_parameters(params):
    query_params = []
    other_params = []
    for param in params:
        if 'Query' in param.metadata:
            query_params.append(param)
        else:
            other_params.append(param)
    return query_params, other_params


def extract_path_parameters(params, url):
    """
    Return list of field_infos which are path variables, another list of
    field_infos which are not path parameters and the url that eventually
    changed due to mismatching param names.
    An example of a URL that changes:
    /vcenter/resource-pool/{resource-pool} to
    /vcenter/resource-pool/{resource_pool}
    """
    # Regex to look for {} placeholders with a group to match only the parameter name
    re_path_param = re.compile('{(.+?)}')
    path_params = []
    other_params = list(params)
    new_url = url
    for path_param_name_match in re_path_param.finditer(url):
        path_param_placeholder = path_param_name_match.group(1)
        path_param_info = None
        for param in other_params:
            if is_param_path_variable(param, path_param_placeholder):
                path_param_info = param
                if param.name != path_param_placeholder:
                    new_url = new_url.replace(path_param_name_match.group(), '{' + param.name + '}')
                break
        if path_param_info is None:
            eprint('%s parameter from %s is not found among the operation\'s parameters'
                   % (path_param_placeholder, url))
        else:
            path_params.append(path_param_info)
            other_params.remove(path_param_info)
    return path_params, other_params, new_url


def is_param_path_variable(param, path_param_placeholder):
    if param.name == path_param_placeholder:
        return True
    if 'PathVariable' not in param.metadata:
        return False
    return param.metadata['PathVariable'].elements['value'].string_value == path_param_placeholder


def flatten_query_param_spec(query_param_info, type_dict, structure_svc, enum_svc, endpoint):
    """
    Flattens query parameters specs.
    1. Create a query parameter for every field in spec.
        Example 1:
            consider datacenter get which accepts optional filterspec.
            Optional<Datacenter.FilterSpec> filter)
            The method would convert the filterspec to 3 separate query parameters
            filter.datacenters, filter.names and filter.folders.
        Example 2:
            consider /vcenter/deployment/install/initial-config/remote-psc/thumbprint get
            which accepts parameter
            vcenter.deployment.install.initial_config.remote_psc.thumbprint.remote_spec.
            The two members defined under remote_spec
            address and https_port are converted to two separate query parameters
            address(required) and https_port(optional).
    2. The field info is simple type. i.e the type is string, integer
        then it is converted it to swagger parameter.
        Example:
            consider /com/vmware/content/library/item get
            which accepts parameter 'library_id'. The field is converted
             to library_id query parameter.
    3. This field has references to a spec but the spec is not
        a complex type and does not have property 'properties'.
        i.e the type is string, integer. The members defined under the spec are
        converted to query parameter.
        Example:
            consider /appliance/update/pending get which accepts two parameter
            'source_type' and url. Where source_type is defined in the spec
            'appliance.update.pending.source_type' and field url
            is of type string.
            The fields 'source_type' and 'url' are converted to query parameter
             of type string.
    """
    prop_array = []
    parameter_obj = {}
    tpHandler = typeHandler(endpoint)
    tpHandler.visit_type_category(query_param_info.type, parameter_obj, type_dict, structure_svc, enum_svc)
    if '$ref' in parameter_obj:
        reference = parameter_obj['$ref'].replace('#/definitions/', '')
        type_ref = type_dict.get(reference, None)
        if type_ref is None:
            return None
        if 'properties' in type_ref:
            for property_name, property_value in six.iteritems(type_ref['properties']):
                prop = {'in': 'query', 'name': query_param_info.name + '.' + property_name}
                if endpoint == "api":
                    prop = {'in': 'query', 'name': property_name}
                if 'type' in property_value:
                    prop['type'] = property_value['type']
                    if prop['type'] == 'array':
                        prop['collectionFormat'] = 'multi'
                        prop['items'] = property_value['items']
                        if '$ref' in property_value['items']:
                            ref = property_value['items']['$ref'].replace('#/definitions/', '')
                            type_ref = type_dict[ref]
                            prop['items'] = type_ref
                            if 'description' in prop['items']:
                                del prop['items']['description']
                    if 'description' in property_value:
                        prop['description'] = property_value['description']
                elif '$ref' in property_value:
                    reference = property_value['$ref'].replace('#/definitions/', '')
                    prop_obj = type_dict[reference]
                    if 'type' in prop_obj:
                        prop['type'] = prop_obj['type']
                        # Query parameter's type is object, Coverting it to string given type object for query is not supported by swagger 2.0.
                        if prop['type'] == "object":
                            prop['type' ] = "string" 
                    if 'enum' in prop_obj:
                        prop['enum'] = prop_obj['enum']
                    if 'description' in prop_obj:
                        prop['description'] = prop_obj['description']
                if 'required' in type_ref:
                    if property_name in type_ref['required']:
                        prop['required'] = True
                    else:
                        prop['required'] = False
                prop_array.append(prop)
        else:
            prop = {'in': 'query', 'name': query_param_info.name, 'description': type_ref['description'],
                    'type': type_ref['type']}
            if 'enum' in type_ref:
                prop['enum'] = type_ref['enum']
            if 'required' not in parameter_obj:
                prop['required'] = True
            else:
                prop['required'] = parameter_obj['required']
            prop_array.append(prop)
    else:
        parameter_obj['in'] = 'query'
        parameter_obj['name'] = query_param_info.name
        parameter_obj['description'] = query_param_info.documentation
        if 'required' not in parameter_obj:
            parameter_obj['required'] = True
        prop_array.append(parameter_obj)
    return prop_array


def process_get_request(url, params, type_dict, structure_svc, enum_svc, endpoint):
    param_array = []
    path_param_list, other_params_list, new_url = extract_path_parameters(params, url)
    
    for field_info in path_param_list:
        parameter_obj = convert_field_info_to_swagger_parameter('path', field_info,
                                                                type_dict, structure_svc, enum_svc, endpoint)
        param_array.append(parameter_obj)

    if endpoint == "api":
        ## Query 
        query_param_list, other_params_list = extract_query_parameters(other_params_list)
        for query_param in query_param_list:
            parameter_obj = convert_field_info_to_swagger_parameter('query', query_param,
                                                                type_dict, structure_svc, enum_svc, endpoint)
            param_array.append(parameter_obj)

    # process query parameters
    for field_info in other_params_list:
        # See documentation of method flatten_query_param_spec to understand
        # handling of all the query parameters; filter as well as non filter
        flattened_params = flatten_query_param_spec(field_info, type_dict, structure_svc, enum_svc, endpoint)
        if flattened_params is not None:
            param_array = param_array + flattened_params
    return param_array, new_url


def wrap_body_params(service_name, operation_name, body_param_list, type_dict, structure_svc,
                     enum_svc, endpoint):
    """
    Creates a  json object wrapper around request body parameters. parameter names are used as keys and the
    parameters as values.
    For instance, datacenter create operation takes CreateSpec whose parameter name is spec.
    This method creates a json wrapper object
    datacenter.create {
     'spec' : {spec obj representation  }
    }
    """
    # todo:
    # not unique enough. make it unique
    wrapper_name = service_name + '_' + operation_name
    body_obj = {}
    properties_obj = {}
    if endpoint == "rest":
        body_obj['type'] =  'object'
        body_obj['properties'] = properties_obj
    
    required = []
    tpHandler = typeHandler(endpoint)
    for param in body_param_list:
        
        parameter_obj = {}
        tpHandler.visit_type_category(param.type, parameter_obj, type_dict, structure_svc, enum_svc)
        parameter_obj['description'] = param.documentation
        if endpoint == "rest":
            properties_obj[param.name] = parameter_obj
            if 'required' not in parameter_obj:
                required.append(param.name)
            elif parameter_obj['required'] == 'true':
                required.append(param.name)
        elif endpoint == "api":
            body_obj.update(parameter_obj)

    parameter_obj = {'in': 'body', 'name': 'request_body'}
    if len(required) > 0:
        body_obj['required'] = required
        parameter_obj['required'] = True
    elif 'required' in body_obj:
        del body_obj['required']

    type_dict[wrapper_name] = body_obj

    schema_obj = {'$ref': '#/definitions/' + wrapper_name}
    parameter_obj['schema'] = schema_obj
    return parameter_obj


def process_put_post_patch_request(url, service_name, operation_name, params,
                                   type_dict, structure_svc, enum_svc, endpoint):
    """
    Handles http post/put/patch request.
    todo: handle query, formData and header parameters
    """
    ## Path
    path_param_list, other_param_list, new_url = extract_path_parameters(params, url)
    par_array = []
    for field_info in path_param_list:
        parx = convert_field_info_to_swagger_parameter('path', field_info, type_dict,
                                                       structure_svc, enum_svc, endpoint)
        par_array.append(parx)

    if endpoint == "api":
        ## Body
        body_param_list, other_param_list =  extract_body_parameters(other_param_list)
    else:
        body_param_list = other_param_list

    if body_param_list:
        parx = wrap_body_params(service_name, operation_name, body_param_list, type_dict,
                                structure_svc, enum_svc, endpoint)
        if parx is not None:
            par_array.append(parx)

    if endpoint == "api":
        ## Query 
        query_param_list, other_param_list = extract_query_parameters(other_param_list)
        for query_param in query_param_list:
            parx = convert_field_info_to_swagger_parameter('query', query_param, type_dict,
                                                        structure_svc, enum_svc, endpoint)
            par_array.append(parx)

        # process query parameters
        for field_info in other_param_list:
            # See documentation of method flatten_query_param_spec to understand
            # handling of all the query parameters; filter as well as non filter
            flattened_params = flatten_query_param_spec(field_info, type_dict, structure_svc, enum_svc, endpoint)
            if flattened_params is not None:
                par_array = par_array + flattened_params

    return par_array, new_url


def process_delete_request(url, params, type_dict, structure_svc, enum_svc, endpoint):
    path_param_list, other_params, new_url = extract_path_parameters(params, url)
    param_array = []
    for field_info in path_param_list:
        parx = convert_field_info_to_swagger_parameter('path', field_info, type_dict,
                                                       structure_svc, enum_svc, endpoint)
        param_array.append(parx)
    for field_info in other_params:
        parx = convert_field_info_to_swagger_parameter('query', field_info, type_dict, structure_svc, enum_svc, endpoint)
        param_array.append(parx)
    return param_array, new_url


def handle_request_mapping(url, method_type, service_name, operation_name, params_metadata,
                           type_dict, structure_svc, enum_svc, endpoint):
    if method_type in ('post', 'put', 'patch'):
        return process_put_post_patch_request(url, service_name, operation_name,
                                              params_metadata, type_dict, structure_svc,
                                              enum_svc, endpoint)
    if method_type == 'get':
        return process_get_request(url, params_metadata, type_dict,
                                   structure_svc, enum_svc, endpoint)
    if method_type == 'delete':
        return process_delete_request(url, params_metadata, type_dict,
                                      structure_svc, enum_svc, endpoint)


def find_url(list_of_links):
    """
    There are many apis which get same work done.
    The idea here is to show the best one.
    Here is the logic for picking the best one.
    * if there is only one element in the list, the choice is obvious.
    * if there are more than one:
        return for a link which does not contain "~action" in them and which contain "id:{}" in them.
    """
    if len(list_of_links) == 1:
        return list_of_links[0]['href'], list_of_links[0]['method']

    non_action_link = None
    for link in list_of_links:
        if '~action=' not in link['href']:
            if "id:" in link['href']:
                return link['href'], link['method']
            if non_action_link is None:
                non_action_link = link
    if non_action_link is None:
        # all links have ~action in them. check if any of them has id: and return it.
        for link in list_of_links:
            if "id:" in link['href']:
                return link['href'], link['method']

        # all links have ~action in them and none of them have id: (pick any one)
        return list_of_links[0]['href'], list_of_links[0]['method']

    return non_action_link['href'], non_action_link['method']


def contains_rm_annotation(service_info):
    for operation in service_info.operations.values():
        if 'RequestMapping' not in operation.metadata:
            return False
    return True


def get_path(operation_info, http_method, url, service_name, type_dict, structure_dict, enum_dict,
             operation_id, http_error_map, endpoint):
    documentation = operation_info.documentation
    op_metadata = operation_info.metadata
    params = operation_info.params
    errors = operation_info.errors
    output = operation_info.output
    http_method = http_method.lower()
    consumes_json = find_consumes(http_method)
    produces = None
    par_array, url = handle_request_mapping(url, http_method, service_name,
                                            operation_id, params, type_dict,
                                            structure_dict, enum_dict, endpoint)
    response_map = populate_response_map(output,
                                         errors,
                                         http_error_map, type_dict, structure_dict, enum_dict, op_metadata, service_name, operation_id, endpoint)
    endpoint_with_url = '/' + endpoint + url
    path = build_path(service_name,
                      http_method,
                      endpoint_with_url,
                      documentation, par_array, operation_id=operation_id,
                      responses=response_map,
                      consumes=consumes_json, produces=produces)
    return path


def api_get_url_and_method(metadata):
    for method in metadata.keys():
        if method in ['POST', 'GET', 'DELETE', 'PUT', 'PATCH']: 
            url_path = metadata[method].elements["path"].string_value
            return method, url_path


def process_service_urls(package_name, service_urls, output_dir, structure_dict, enum_dict,
                         service_dict, service_url_dict, http_error_map, rest_navigation_url):

    print('processing package ' + package_name + os.linesep)
    type_dict = {}
    path_list = []
    for service_url in service_urls:
        # print(service_url)
        service_name, service_end_point = service_url_dict.get(service_url, None)
        service_info = service_dict.get(service_name, None)
        if service_info is None:
            continue
        if is_filtered(service_info.metadata):
            continue

        ## Processing for /api end point
        if service_end_point == '/api':

            for operation_id, operation_info in service_info.operations.items():
                method, url = api_get_url_and_method(operation_info.metadata)

                # check for query parameters
                if 'params' in operation_info.metadata[method].elements:
                    element_value = operation_info.metadata[method].elements['params']
                    params = "&".join(element_value.list_value)
                    url = url + '?' + params

                path = get_path(operation_info, method, url, service_name, type_dict, structure_dict, enum_dict,
                                operation_id, http_error_map, "api")
                path_list.append(path)
            continue

        ## Processing for /rest end point
        if contains_rm_annotation(service_info):
            for operation in service_info.operations.values():
                url, method = find_url_method(operation)
                operation_id = operation.name
                op_metadata = service_info.operations[operation_id].metadata
                if is_filtered(op_metadata):
                    continue
                operation_info = service_info.operations.get(operation_id)

                path = get_path(operation_info, method, url, service_name, type_dict, structure_dict, enum_dict,
                                operation_id, http_error_map, "rest")
                path_list.append(path)
            continue

        # use rest navigation service to get the REST mappings for a service.
        service_operations = get_json(rest_navigation_url + service_url + '?~method=OPTIONS', False)
        if service_operations is None:
            continue

        for service_operation in service_operations:
            service_name = service_operation['service']
            # service_info must be re-assigned when service_operations are obtained through ?~method=OPTIONS.
            # this is because all service operations matching the prefix of the service is returned instead of returning
            # only operations which has exact match.
            # for example OPTIONS on com.vmware.content.library returns operations from following services
            # instead of just com.vmware.content.library.item
            # com.vmware.content.library.item.storage
            # com.vmware.content.library.item
            # com.vmware.content.library.item.file
            # com.vmware.content.library.item.update_session
            # com.vmware.content.library.item.updatesession.file
            service_info = service_dict.get(service_name, None)
            if service_info is None:
                continue
            operation_id = service_operation['name']
            if operation_id not in service_info.operations:
                continue
            op_metadata = service_info.operations[operation_id].metadata
            if is_filtered(op_metadata):
                continue
            url, method = find_url(service_operation['links'])
            url = get_service_path_from_service_url(url, rest_navigation_url)
            operation_info = service_info.operations.get(operation_id)
            path = get_path(operation_info, method, url, service_name, type_dict, structure_dict, enum_dict,
                            operation_id, http_error_map, "rest")
            path_list.append(path)
    path_dict = convert_path_list_to_path_map(path_list)
    cleanup(path_dict=path_dict, type_dict=type_dict)
    process_output(path_dict, type_dict, output_dir, package_name)


def get_input_params():
    """
    Gets input parameters from command line
    :return:
    """
    parser = argparse.ArgumentParser(description='Generate swagger.json files for apis on vcenter')
    parser.add_argument('-m', '--metadata-url', help='URL of the metadata API')
    parser.add_argument('-rn', '--rest-navigation-url', help='URL of the rest-navigation API')
    parser.add_argument('-vc', '--vcip', help='IP Address of vCenter Server. If specified, would be used'
                                              ' to calculate metadata-url and rest-navigation-url')
    parser.add_argument('-o', '--output', help='Output directory of swagger files. if not specified,'
                                               ' current working directory is chosen as output directory')
    parser.add_argument('-s', '--tag-separator', default='/', help='Separator to use in tag name')
    parser.add_argument('-k', '--insecure', action='store_true', help='Bypass SSL certificate validation')
    parser.add_argument("-uo", "--unique-operation-ids", required=False, nargs='?', const=True, default=False,
                        help="Pass this parameter to generate Unique Operation Ids.")
    parser.add_argument("-c", "--metamodel-components", required=False, nargs='?', const=True, default=False,
                        help="Pass this parameter to save each metamodel component as a new json file")
    parser.add_argument('--host', help='Domain name or IP address (IPv4) of the host that serves the API. '
                                             'Default value is "<vcenter>"')
    parser.add_argument('-ef', '--enablefiltering', dest='filtering',
                        help='Filters internal and unreleased apis', action='store_true')
    parser.set_defaults(filtering=False)
    args = parser.parse_args()
    metadata_url = args.metadata_url
    rest_navigation_url = args.rest_navigation_url
    vcip = args.vcip
    if vcip is not None:
        if metadata_url is None:
            metadata_url = 'https://%s/api' % vcip
        if rest_navigation_url is None:
            rest_navigation_url = 'https://%s/rest' % vcip

    if metadata_url is None or rest_navigation_url is None:
        raise ValueError('metadataUrl and restNavigationUrl are required parameters')
    metadata_url = metadata_url.rstrip('/')
    rest_navigation_url = rest_navigation_url.rstrip('/')
    output_dir = args.output
    if args.host is not None:
        global API_SERVER_HOST
        API_SERVER_HOST = args.host
    if output_dir is None:
        output_dir = os.getcwd()
    verify = not args.insecure
    global GENERATE_UNIQUE_OP_IDS
    GENERATE_UNIQUE_OP_IDS = args.unique_operation_ids
    global TAG_SEPARATOR
    TAG_SEPARATOR = args.tag_separator
    global enable_filtering
    enable_filtering = args.filtering
    global GENERATE_METAMODEL
    GENERATE_METAMODEL = args.metamodel_components
    return metadata_url, rest_navigation_url, output_dir, verify


def get_component_service(connector):
    stub_config = StubConfigurationFactory.new_std_configuration(connector)
    component_svc = metamodel_client.Component(stub_config)
    return component_svc


def get_service_urls_from_rest_navigation(rest_navigation_url, verify):
    component_services_urls = get_component_services_urls(rest_navigation_url, verify)
    return get_all_services_urls(component_services_urls, verify)


def get_service_path_from_service_url(service_url, base_url):
    if not service_url.startswith(base_url):
        return service_url

    return service_url[len(base_url):]


def find_url_method(opinfo):
    """
    Given OperationInfo, find url and method if it exists
    :param opinfo:
    :return:
    """
    params = None
    url = None
    method = None
    if 'RequestMapping' in opinfo.metadata:
        element_map = opinfo.metadata['RequestMapping']
        if 'value' in element_map.elements:
            element_value = element_map.elements['value']
            url = find_string_element_value(element_value)
        if 'method' in element_map.elements:
            element_value = element_map.elements['method']
            method = find_string_element_value(element_value)
        if 'params' in element_map.elements:
            element_value = element_map.elements['params']
            params = find_string_element_value(element_value)
    if params is not None:
        url = url + '?' + params
    return url, method


def objectTodict(obj):
    objtype = type(obj)
    if objtype is int or objtype is str or objtype is float or objtype == type(None) or objtype is bool:
        pass
    elif objtype is dict:
        temp = {}
        for key, value in obj.items():
            temp[key] = objectTodict(value)

        obj = temp
    elif objtype is list:
        temp = []
        for value in obj:
            temp.append(objectTodict(value))
        obj = temp
    else:
        if obj.__dict__ != {}:
            obj = objectTodict(obj.__dict__)
        
    return obj


def populate_dicts(component_svc, enumeration_dict, structure_dict, service_dict, service_urls_map, base_url):
    components = component_svc.list()
    for component in components:
        component_data = component_svc.get(component)
        global GENERATE_METAMODEL
        if GENERATE_METAMODEL:
            if not os.path.exists('metamodel'):
                os.mkdir('metamodel')
            write_json_data_to_file('metamodel/'+component+'.json', objectTodict(component_data))
        component_packages = component_data.info.packages
        for package in component_packages:
            package_info = component_packages.get(package)
            for enumeration, enumeration_info in package_info.enumerations.items():
                enumeration_dict[enumeration] = enumeration_info
            for structure, structure_info in package_info.structures.items():
                structure_dict[structure] = structure_info
                for enum_name, enum_info in structure_info.enumerations.items():
                    enumeration_dict[enum_name] = enum_info
            for service, service_info in package_info.services.items():
                service_dict[service] = service_info
                service_urls_map[get_service_url_from_service_id(base_url, service)] = service
                for structure_name, structure_info in service_info.structures.items():
                    structure_dict[structure_name] = structure_info
                    for et1, et_info1 in structure_info.enumerations.items():
                        enumeration_dict[et1] = et_info1
                for enum_name, enum_info in service_info.enumerations.items():
                    enumeration_dict[enum_name] = enum_info


def get_service_url_from_service_id(base_url, service_id):
    replaced_string = service_id.replace('.', '/')
    return base_url + '/' + replaced_string.replace('_', '-')


def add_service_urls_using_metamodel(service_urls_map, service_dict, rest_navigation_url):

    package_dict = {}

    all_rest_services = []
    for i in service_urls_map:
        all_rest_services.append(service_urls_map[i][0])

    rest_services = {}
    for k, v in service_urls_map.items():
        rest_services.update({
            v:k
        })

    for service in service_dict:
        # if service not in all_rest_services:
        check, path_list = get_paths_inside_metamodel( service, service_dict )
        if check:
            for path in path_list:
                service_urls_map[path] = (service, '/api')
                package_name = path.split('/')[1]
                pack_arr = package_dict.get(package_name, [])
                if pack_arr == []:
                    package_dict[package_name] = pack_arr
                pack_arr.append(path)
        else:
            service_url = rest_services.get(service, None)
            if service_url is not None:
                service_path = get_service_path_from_service_url(service_url, rest_navigation_url)
                service_urls_map[service_path] = (service, '/rest')
                package = service_path.split('/')[3]
                if package in package_dict:
                    packages = package_dict[package]
                    packages.append(service_path)
                else:
                    package_dict.setdefault(package, [service_path])
            else:
                print("Service doesnot belong to either /api or /rest ", service)
    return package_dict


def get_paths_inside_metamodel(service, service_dict):
    path_list = set()
    for operation_id in service_dict[service].operations.keys():
        for request in service_dict[service].operations[operation_id].metadata.keys():
            if request.lower() in ('post', 'put', 'patch', 'get', 'delete'):
                path_list.add(service_dict[service].operations[operation_id]
                              .metadata[request].elements['path'].string_value)
    
    if path_list == set():
        return False, []

    return True, sorted(list(path_list))


def main():
    # Get user input.
    metadata_api_url, rest_navigation_url, output_dir, verify = get_input_params()
    # Maps enumeration id to enumeration info
    enumeration_dict = {}
    # Maps structure_id to structure_info
    structure_dict = {}
    # Maps service_id to service_info
    service_dict = {}
    # Maps service url to service id
    service_urls_map = {}

    start = timeit.default_timer()
    print('Trying to connect ' + metadata_api_url)
    session = requests.session()
    session.verify = False
    connector = get_requests_connector(session, url=metadata_api_url)
    if not enable_filtering:
        connector.set_application_context(ApplicationContext({SHOW_UNRELEASED_APIS: "True"}))
    print('Connected to ' + metadata_api_url)
    component_svc = get_component_service(connector)
    populate_dicts(component_svc, enumeration_dict, structure_dict, service_dict, service_urls_map, rest_navigation_url)

    if enable_filtering:
        # If filtering is enabled, get service urls from rest navigation
        # because rest navigation takes care of filtering.
        # else, Get service urls from metamodel metadata.
        service_urls_map = get_service_urls_from_rest_navigation(rest_navigation_url, verify)
    http_error_map = HttpErrorMap(component_svc)

    # package_dict holds list of all service urls which come under /api and /rest
    package_dict = add_service_urls_using_metamodel(service_urls_map, service_dict, rest_navigation_url)

    threads = []
    for package, service_urls in six.iteritems(package_dict):
        worker = threading.Thread(target=process_service_urls, args=(
            package, service_urls, output_dir, structure_dict, enumeration_dict, service_dict, service_urls_map
            , http_error_map, rest_navigation_url))
        worker.daemon = True
        worker.start()
        threads.append(worker)
    
    for worker in threads:
        worker.join()

    # api.json contains list of packages which is used by UI to dynamically populate dropdown.
    api_files_list = []
    for name in list(package_dict.keys()):
        api_files_list.append(name)

    api_files = { 'files': api_files_list }
    write_json_data_to_file(output_dir + os.path.sep + 'api.json', api_files)
    stop = timeit.default_timer()
    print('Generated swagger files at ' + output_dir + ' for ' + metadata_api_url + ' in ' + str(
        stop - start) + ' seconds')


if __name__ == '__main__':
    main()
