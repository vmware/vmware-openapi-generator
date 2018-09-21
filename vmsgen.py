#!/usr/bin/env python

# Copyright 2016-2018 VMware, Inc.
# SPDX-License-Identifier: MIT

# pylint: disable=C0111, E1121, R0913, R0914, R0911, W0703, E1101, C0301, W0511,C0413
from __future__ import print_function
import sys
import os
import argparse
import collections
import timeit
import json
import threading
import re
import copy
import six
import requests
import warnings
from six.moves import http_client
from vmware.vapi.lib.connect import get_requests_connector
from vmware.vapi.stdlib.client.factories import StubConfigurationFactory
from com.vmware.vapi.metadata import metamodel_client

warnings.filterwarnings("ignore")


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


# Specify the SSL Trust path to certificates or False to ignore SSL
VERIFY = False

'''
This script uses metamodel apis and rest navigation to generate swagger compliant json files
for apis available on vcenter.
'''


def build_error_map():
    """
    Builds error_map which maps vapi errors to http status codes.
    """
    error_map = {'vapi.std.errors.already_exists': http_client.BAD_REQUEST,
                 'vapi.std.errors.already_in_desired_state': http_client.BAD_REQUEST,
                 'vapi.std.errors.feature_in_use': http_client.BAD_REQUEST,
                 'vapi.std.errors.internal_server_error': http_client.INTERNAL_SERVER_ERROR,
                 'vapi.std.errors.invalid_argument': http_client.BAD_REQUEST,
                 'vapi.std.errors.invalid_element_configuration': http_client.BAD_REQUEST,
                 'vapi.std.errors.invalid_element_type': http_client.BAD_REQUEST,
                 'vapi.std.errors.invalid_request': http_client.BAD_REQUEST,
                 'vapi.std.errors.not_found': http_client.NOT_FOUND,
                 'vapi.std.errors.operation_not_found': http_client.NOT_FOUND,
                 'vapi.std.errors.not_allowed_in_current_state': http_client.BAD_REQUEST,
                 'vapi.std.errors.resource_busy': http_client.BAD_REQUEST,
                 'vapi.std.errors.resource_in_use': http_client.BAD_REQUEST,
                 'vapi.std.errors.resource_inaccessible': http_client.BAD_REQUEST,
                 'vapi.std.errors.service_unavailable': http_client.SERVICE_UNAVAILABLE,
                 'vapi.std.errors.timed_out': http_client.GATEWAY_TIMEOUT,
                 'vapi.std.errors.unable_to_allocate_resource': http_client.BAD_REQUEST,
                 'vapi.std.errors.unauthenticated': http_client.UNAUTHORIZED,
                 'vapi.std.errors.unauthorized': http_client.FORBIDDEN,
                 'vapi.std.errors.unexpected_input': http_client.BAD_REQUEST,
                 'vapi.std.errors.unsupported': http_client.BAD_REQUEST,
                 'vapi.std.errors.error': http_client.BAD_REQUEST,
                 'vapi.std.errors.concurrent_change': http_client.BAD_REQUEST,
                 'vapi.std.errors.unverified_peer': http_client.BAD_REQUEST}
    return error_map


def load_description():
    """
    Loads description.properties into a dictionary.
    """
    desc = {
        'content': 'VMware vSphere\u00ae Content Library empowers vSphere Admins to effectively manage VM templates, '
                   'vApps, ISO images and scripts with ease.', 'spbm': 'SPBM',
        'vapi': 'vAPI is an extensible API Platform for modelling and delivering APIs/SDKs/CLIs.',
        'vcenter': 'VMware vCenter Server provides a centralized platform for managing your VMware vSphere environments',
        'appliance': 'The vCenter Server Appliance is a preconfigured Linux-based virtual machine optimized for running vCenter Server and associated services.'}
    return desc


def write_json_data_to_file(file_name, json_data):
    """
    Utility method used to write json file.
    """
    with open(file_name, 'w+') as outfile:
        json.dump(json_data, outfile, indent=4)


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


def get_structure_info(struct_type, structure_svc):
    """
    Given a type, return its structure info, if the type is a structure.
    """
    try:
        struct_type_temp = remove_com_vmware(struct_type)
        structure_info = structure_svc.get(struct_type_temp)
        return structure_info
    except Exception as ex:
        eprint("Could not fetch structure info for " + struct_type_temp)
        eprint(ex)
        return None


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
        return 'string', None
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


def visit_type_category(struct_type, new_prop, type_dict, structure_svc, enum_svc):
    if isinstance(struct_type, dict):
        return visit_type_category_dict(struct_type, new_prop, type_dict, structure_svc, enum_svc)
    if struct_type.category == 'BUILTIN':
        visit_builtin(struct_type.builtin_type, new_prop)
    elif struct_type.category == 'GENERIC':
        visit_generic(struct_type.generic_instantiation, new_prop, type_dict, structure_svc,
                      enum_svc)
    elif struct_type.category == 'USER_DEFINED':
        visit_user_defined(struct_type.user_defined_type, new_prop, type_dict, structure_svc,
                           enum_svc)


def visit_type_category_dict(struct_type, new_prop, type_dict, structure_svc, enum_svc):
    if struct_type['category'] == 'BUILTIN':
        visit_builtin(struct_type['builtin_type'], new_prop)
    elif struct_type['category'] == 'GENERIC':
        visit_generic(struct_type['generic_instantiation'], new_prop, type_dict, structure_svc,
                      enum_svc)
    elif struct_type['category'] == 'USER_DEFINED':
        visit_user_defined(struct_type['user_defined_type'], new_prop, type_dict, structure_svc,
                           enum_svc)


def visit_builtin(builtin_type, new_prop):
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


def visit_generic(generic_instantiation, new_prop, type_dict, structure_svc, enum_svc):
    if generic_instantiation.generic_type == 'OPTIONAL':
        new_prop['required'] = False
        visit_type_category(generic_instantiation.element_type, new_prop, type_dict,
                            structure_svc, enum_svc)
    elif generic_instantiation.generic_type == 'LIST':
        new_prop['type'] = 'array'
        visit_type_category(generic_instantiation.element_type, new_prop, type_dict,
                            structure_svc, enum_svc)
    elif generic_instantiation.generic_type == 'SET':
        new_prop['type'] = 'array'
        new_prop['uniqueItems'] = True
        visit_type_category(generic_instantiation.element_type, new_prop, type_dict,
                            structure_svc, enum_svc)
    elif generic_instantiation.generic_type == 'MAP':
        new_type = {'type': 'object', 'properties': {}}
        if generic_instantiation.map_key_type.category == 'USER_DEFINED':
            res_id = generic_instantiation.map_key_type.user_defined_type.resource_id
            res_type = generic_instantiation.map_key_type.user_defined_type.resource_type
            new_type['properties']['key'] = {'$ref': '#/definitions/' + remove_com_vmware(res_id)}
            check_type(res_type, res_id, type_dict, structure_svc, enum_svc)
        else:
            new_type['properties']['key'] = {'type': metamodel_to_swagger_type_converter(
                generic_instantiation.map_key_type.builtin_type)[0]}
        if generic_instantiation.map_value_type.category == 'USER_DEFINED':
            new_type['properties']['value'] = {
                '$ref': '#/definitions/' + remove_com_vmware(
                    generic_instantiation.map_value_type.user_defined_type.resource_id)}
            res_type = generic_instantiation.map_value_type.user_defined_type.resource_type
            res_id = generic_instantiation.map_value_type.user_defined_type.resource_id
            check_type(res_type, res_id, type_dict, structure_svc, enum_svc)
        elif generic_instantiation.map_value_type.category == 'BUILTIN':
            new_type['properties']['value'] = {'type': metamodel_to_swagger_type_converter(
                generic_instantiation.map_value_type.builtin_type)[0]}
        elif generic_instantiation.map_value_type.category == 'GENERIC':
            new_type['properties']['value'] = {}
            visit_generic(generic_instantiation.map_value_type.generic_instantiation,
                          new_type['properties']['value'], type_dict, structure_svc,
                          enum_svc)
        new_prop['type'] = 'array'
        new_prop['items'] = new_type
        if '$ref' in new_prop:
            del new_prop['$ref']


def is_type_builtin(type_):
    type_ = type_.lower()
    typeset = {'binary', 'boolean', 'datetime', 'double', 'dynamicstructure', 'exception',
               'id', 'long', 'opaque', 'secret', 'string', 'uri'}
    if type_ in typeset:
        return True
    return False


def process_structure_info(type_name, structure_info, type_dict, structure_svc, enum_svc):
    new_type = {'type': 'object', 'properties': {}}
    for field in structure_info.fields:
        newprop = {'description': field.documentation}
        if field.type.category == 'BUILTIN':
            visit_builtin(field.type.builtin_type, newprop)
        elif field.type.category == 'GENERIC':
            visit_generic(field.type.generic_instantiation, newprop, type_dict,
                          structure_svc, enum_svc)
        elif field.type.category == 'USER_DEFINED':
            visit_user_defined(field.type.user_defined_type, newprop, type_dict,
                               structure_svc, enum_svc)
        new_type['properties'].setdefault(field.name, newprop)
    required = []
    for property_name, property_value in six.iteritems(new_type['properties']):
        if 'required' not in property_value:
            required.append(property_name)
        else:
            if property_value['required'] == 'true':
                required.append(property_name)
    if not required:
        new_type['required'] = required
    type_dict[type_name] = new_type


def process_enum_info(type_name, enum_info, type_dict):
    enum_type = {'type': 'string', 'description': enum_info.documentation}
    enum_type.setdefault('enum', [value.value for value in enum_info.values])
    type_dict[type_name] = enum_type


def check_type(resource_type, type_name, type_dict, structure_svc, enum_svc):
    if type_name in type_dict or is_type_builtin(type_name):
        return
    if resource_type == 'com.vmware.vapi.structure':
        structure_info = get_structure_info(type_name, structure_svc)
        if structure_info is not None:
            # Mark it as visited to handle recursive definitions. (Type A referring to Type A in one of the fields).
            type_dict[type_name] = {}
            process_structure_info(type_name, structure_info, type_dict, structure_svc, enum_svc)
    else:
        enum_info = get_enum_info(type_name, enum_svc)
        if enum_info is not None:
            # Mark it as visited to handle recursive definitions. (Type A referring to Type A in one of the fields).
            type_dict[type_name] = {}
            process_enum_info(type_name, enum_info, type_dict)


def get_enum_info(type_name, enum_svc):
    """
    Given a type, return its enum info, if the type is enum.
    """
    try:
        type_name_temp = remove_com_vmware(type_name)
        enum_info = enum_svc.get(type_name_temp)
        return enum_info
    except Exception as exception:
        eprint("Could not fetch enum info for " + type_name_temp)
        eprint(exception)
        return None


def visit_user_defined(user_defined_type, newprop, type_dict, structure_svc, enum_svc):
    if user_defined_type.resource_id is None:
        return
    if 'type' in newprop and newprop['type'] == 'array':
        item_obj = {'$ref': '#/definitions/' + remove_com_vmware(user_defined_type.resource_id)}
        newprop['items'] = item_obj
    # if not array, fill in type or ref
    else:
        newprop['$ref'] = '#/definitions/' + remove_com_vmware(user_defined_type.resource_id)

    check_type(user_defined_type.resource_type, user_defined_type.resource_id, type_dict, structure_svc, enum_svc)


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
                                            structure_svc, enum_svc):
    """
    Converts metamodel fieldinfo to swagger parameter.
    """
    parameter_obj = {}
    visit_type_category(input_parameter_obj.type, parameter_obj, type_dict,
                        structure_svc, enum_svc)
    if 'required' not in parameter_obj:
        parameter_obj['required'] = True
    parameter_obj['in'] = param_type
    parameter_obj['name'] = input_parameter_obj.name
    parameter_obj['description'] = input_parameter_obj.documentation
    # $ref should be encapsulated in 'schema' instead of parameter.
    if '$ref' in parameter_obj:
        schema_obj = {'$ref': parameter_obj['$ref']}
        parameter_obj['schema'] = schema_obj
        del parameter_obj['$ref']
    return parameter_obj


def find_output_schema(output, type_dict, structure_svc, enum_svc):
    schema = {}
    visit_type_category(output.type, schema, type_dict, structure_svc, enum_svc)
    return schema


def get_response_object_name(service_id, operation_id):
    if operation_id == 'get':
        return service_id
    return service_id + '.' + operation_id


def populate_response_map(output, errors, error_map, type_dict, structure_svc, enum_svc, service_id, operation_id):
    response_map = {}
    success_response = {'description': output.documentation}
    schema = find_output_schema(output, type_dict, structure_svc, enum_svc)
    # if type of schema is void, don't include it.
    # this prevents showing response as void.
    if schema is not None:
        if not ('type' in schema and schema['type'] == 'void'):
            value_wrapper = {'type': 'object',
                             'properties': {'value': schema},
                             'required': ['value']}
            type_name = get_response_object_name(service_id, operation_id) + '_result'
            if type_name not in type_dict:
                type_dict[remove_com_vmware(type_name)] = value_wrapper
            success_response['schema'] = {"$ref": "#/definitions/" + remove_com_vmware(type_name)}
    # success response is not mapped through metamodel.
    # hardcode it for now.
    response_map[requests.codes.ok] = success_response
    for error in errors:
        structure_id = remove_com_vmware(error.structure_id)
        status_code = error_map[structure_id]
        check_type('com.vmware.vapi.structure', structure_id, type_dict, structure_svc, enum_svc)
        schema_obj = {'type': 'object', 'properties': {'type': {'type': 'string'},
                                                       'value': {'$ref': '#/definitions/' + structure_id}}}
        type_dict[error.structure_id + '_error'] = schema_obj
        response_obj = {'description': error.documentation,
                        'schema': {'$ref': '#/definitions/' + structure_id + '_error'}}
        response_map[status_code] = response_obj
    return response_map


def post_process_path(path_obj):
    # Temporary fixes necessary for generated spec files.
    # Hardcode for now as it is not available from metadata.
    if path_obj['path'] == '/com/vmware/cis/session' and path_obj['method'] == 'post':
        header_parameter = {'in': 'header', 'required': 'true', 'type': 'string',
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
    if service_name is not None:

        splits = service_name.split('.')
        splits = splits[3:]
        tag = ''
        for split in splits:
            # todo:
            # Need to add space here, otherwise swagger-ui breaks. figure out why.
            tag += split + '/'
        # Not adding the trailing space.
        # It leads to _ appearing in the Service and Method names
        path_obj['tags'] = [tag[0:len(tag) - 1]]
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
        if 'properties' in type_object:
            properties = type_object['properties']
            for _, property_value in six.iteritems(properties):
                if 'required' in property_value and isinstance(property_value['required'], bool):
                    del property_value['required']
    for _, path_value in six.iteritems(path_dict):
        for _, method_value in six.iteritems(path_value):
            if 'path' in method_value:
                del method_value['path']
            if 'method' in method_value:
                del method_value['method']


def process_output(path_dict, type_dict, output_dir, output_filename):
    description_map = load_description()
    new_type_dict = {}
    for key, value in type_dict.items():
        new_type_dict[remove_com_vmware(key)] = type_dict.get(key)
    swagger_template = {'swagger': '2.0',
                        'info': {'description': description_map.get(output_filename, ''),
                                 'title': output_filename,
                                 'termsOfService': 'http://swagger.io/terms/',
                                 'version': '2.0.0'}, 'host': '',
                        'basePath': '/rest', 'tags': [],
                        'schemes': ['https', 'http'],
                        'paths': collections.OrderedDict(sorted(path_dict.items())),
                        'definitions': collections.OrderedDict(sorted(new_type_dict.items()))}
    write_json_data_to_file(output_dir + os.path.sep + output_filename + '.json', swagger_template)


def find_consumes(method_type):
    """
    Determine mediaType for input parameters in request body.
    """
    if method_type in ('get', 'delete'):
        return None
    return ['application/json']


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
            eprint(
                '%s parameter from %s is not found among the operation\'s parameters' % (path_param_placeholder, url))
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


def flatten_filter_spec(field_info, type_dict, structure_svc, enum_svc):
    """
    Flattens filterspec.
    This method creates a separate query parameter for every field in filterspec.
    consider example of datacenter get which accepts optional filterspec.
    Optional<Datacenter.FilterSpec> filter)
    gets converted to 3 separate query parameters
    filter.datacenters, filter.names, filter.folders.
    """
    name = field_info.name
    new_prop = {}
    visit_type_category(field_info.type, new_prop, type_dict, structure_svc, enum_svc)
    reference = new_prop['$ref']
    reference = reference.replace('#/definitions/', '')
    type_ref = type_dict.get(reference, None)
    if type_ref is None:
        return None
    prop_array = []
    for property_name, property_value in six.iteritems(type_ref['properties']):
        prop = {'in': 'query', 'name': name + '.' + property_name}
        if 'type' in property_value:
            prop['type'] = property_value['type']
            if prop['type'] == 'array':
                prop['collectionFormat'] = 'multi'
                prop['items'] = property_value['items']
                if '$ref' in property_value['items']:
                    ref = property_value['items']['$ref']
                    ref = ref.replace('#/definitions/', '')
                    type_ref = type_dict[ref]
                    prop['items'] = type_ref
                    if 'description' in prop['items']:
                        del prop['items']['description']
            if 'description' in property_value:
                prop['description'] = property_value['description']
        elif '$ref' in property_value:
            reference = property_value['$ref']
            reference = reference.replace('#/definitions/', '')
            prop_obj = type_dict[reference]
            if 'type' in prop_obj:
                prop['type'] = prop_obj['type']
            if 'enum' in prop_obj:
                prop['enum'] = prop_obj['enum']
            if 'description' in prop_obj:
                prop['description'] = prop_obj['description']
        prop_array.append(prop)
    return prop_array


def process_get_request(url, params, type_dict, structure_svc, enum_svc):
    param_array = []
    path_param_list, query_param_list, new_url = extract_path_parameters(params, url)
    for field_info in path_param_list:
        parameter_obj = convert_field_info_to_swagger_parameter('path', field_info,
                                                                type_dict, structure_svc,
                                                                enum_svc)
        param_array.append(parameter_obj)
    # process query parameters
    for field_info in query_param_list:
        # this is how we determine, if input parameter is a filterspec.
        if field_info.name == 'filter':
            flattened_params = flatten_filter_spec(field_info, type_dict, structure_svc,
                                                   enum_svc)
            if flattened_params is not None:
                param_array[1:1] = flattened_params
    return param_array, new_url


def wrap_body_params(service_name, operation_name, body_param_list, type_dict, structure_svc,
                     enum_svc):
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
    body_obj = {'type': 'object'}
    properties_obj = {}
    body_obj['properties'] = properties_obj
    required = []
    name_array = []
    for param in body_param_list:
        parameter_obj = {}
        visit_type_category(param.type, parameter_obj, type_dict, structure_svc,
                            enum_svc)
        name_array.append(param.name)
        parameter_obj['description'] = param.documentation
        properties_obj[param.name] = parameter_obj
        if 'required' not in parameter_obj:
            required.append(param.name)
        else:
            if parameter_obj['required'] == 'true':
                required.append(param.name)

    parameter_obj = {'in': 'body', 'name': 'request_body'}
    if not required:
        body_obj['required'] = required
        parameter_obj['required'] = True

    type_dict[remove_com_vmware(wrapper_name)] = body_obj

    schema_obj = {'$ref': '#/definitions/' + remove_com_vmware(wrapper_name)}
    parameter_obj['schema'] = schema_obj
    return parameter_obj


def process_put_post_patch_request(url, service_name, operation_name, params,
                                   type_dict, structure_svc, enum_svc):
    """
    Handles http post/put/patch request.
    todo: handle query, formData, header parameters
    """
    path_param_list, body_param_list, new_url = extract_path_parameters(params, url)
    par_array = []
    for field_info in path_param_list:
        parx = convert_field_info_to_swagger_parameter('path', field_info, type_dict,
                                                       structure_svc, enum_svc)
        par_array.append(parx)

    if body_param_list:
        parx = wrap_body_params(service_name, operation_name, body_param_list, type_dict,
                                structure_svc, enum_svc)
        if parx is not None:
            par_array.append(parx)
    return par_array, new_url


def process_delete_request(url, params, type_dict, structure_svc, enum_svc):
    path_param_list, other_params, new_url = extract_path_parameters(params, url)
    param_array = []
    for field_info in path_param_list:
        parx = convert_field_info_to_swagger_parameter('path', field_info, type_dict,
                                                       structure_svc, enum_svc)
        param_array.append(parx)
    for field_info in other_params:
        parx = convert_field_info_to_swagger_parameter('query', field_info, type_dict, structure_svc, enum_svc)
        param_array.append(parx)
    return param_array, new_url


def handle_request_mapping(url, method_type, service_name, operation_name, params_metadata,
                           type_dict, structure_svc, enum_svc):
    if method_type in ('post', 'put', 'patch'):
        return process_put_post_patch_request(url, service_name, operation_name,
                                              params_metadata, type_dict, structure_svc,
                                              enum_svc)
    if method_type == 'get':
        return process_get_request(url, params_metadata, type_dict,
                                   structure_svc, enum_svc)
    if method_type == 'delete':
        return process_delete_request(url, params_metadata, type_dict,
                                      structure_svc, enum_svc)


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


def get_path(operation_info, http_method, url, service_name, type_dict, structure_dict, enum_dict, operation_id,
             error_map):
    documentation = operation_info.documentation
    params = operation_info.params
    errors = operation_info.errors
    output = operation_info.output
    http_method = http_method.lower()
    consumes_json = find_consumes(http_method)
    produces = None
    par_array, url = handle_request_mapping(url, http_method, service_name,
                                            operation_id, params, type_dict,
                                            structure_dict, enum_dict)
    response_map = populate_response_map(output,
                                         errors,
                                         error_map, type_dict, structure_dict, enum_dict, service_name, operation_id)

    path = build_path(service_name,
                      http_method,
                      url,
                      documentation, par_array, operation_id=operation_id,
                      responses=response_map,
                      consumes=consumes_json, produces=produces)
    return path


def process_service_urls(package_name, service_urls, output_dir, structure_dict, enum_dict,
                         service_dict, service_url_dict, error_map, base_url):
    print('processing package ' + package_name + os.linesep)
    type_dict = {}
    path_list = []
    for service_url in service_urls:
        service_name = service_url_dict.get(service_url, None)
        service_info = service_dict.get(service_name, None)
        if service_info is None:
            continue

        if contains_rm_annotation(service_info):
            for operation in service_info.operations.values():
                url, method = find_url_method(operation)
                operation_id = operation.name
                operation_info = service_info.operations.get(operation_id)

                path = get_path(operation_info, method, url, service_name, type_dict, structure_dict, enum_dict,
                                operation_id, error_map)
                path_list.append(path)
            continue

        # use rest navigation service to get the REST mappings for a service.
        service_operations = get_json(service_url + '?~method=OPTIONS', False)
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
            # com.vmware.content.libary.item
            # com.vmware.content.library.item.update_session
            # com.vmware.content.library.item.updatesession.file
            service_info = service_dict.get(service_name, None)
            if service_info is None:
                continue
            operation_id = service_operation['name']
            if operation_id not in service_info.operations:
                continue
            url, method = find_url(service_operation['links'])
            url = get_service_path_from_service_url(url, base_url)
            operation_info = service_info.operations.get(operation_id)
            path = get_path(operation_info, method, url, service_name, type_dict, structure_dict, enum_dict,
                            operation_id, error_map)
            path_list.append(path)
    pathdict = convert_path_list_to_path_map(path_list)
    cleanup(path_dict=pathdict, type_dict=type_dict)
    process_output(pathdict, type_dict, output_dir, package_name)


def get_input_params():
    '''
    Get input parameters from command line
    :return:
    '''
    parser = argparse.ArgumentParser(
        description='Generate swagger.json files for apis on vcenter')
    parser.add_argument('-m', '--metadata-url', help='URL of the metadata API')
    parser.add_argument('-rn', '--rest-navigation-url', help='URL of the rest-navigation API')
    parser.add_argument('-vc', '--vcip',
                        help='IP Address of vCenter Server. If specified, would be used to calculate metadata-url and rest-navigation-url')
    parser.add_argument('-o', '--output',
                        help='Output directory of swagger.json file. if not specified, current working directory is chosen as output directory')
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
    if output_dir is None:
        output_dir = os.getcwd()
    return metadata_url, rest_navigation_url, output_dir


def get_component_service(connector):
    stub_config = StubConfigurationFactory.new_std_configuration(connector)
    component_svc = metamodel_client.Component(stub_config)
    return component_svc


def get_service_urls_from_rest_navigation(rest_navigation_url):
    component_services_urls = get_component_services_urls(rest_navigation_url, VERIFY)
    return get_all_services_urls(component_services_urls, VERIFY)


def categorize_service_urls_by_package_names(service_urls_map, base_url):
    package_dict = {}
    for service_url in service_urls_map:
        # service_url = u'https://vcip/rest/com/vmware/vapi/metadata/metamodel/resource/model'
        # service_path = /com/vmware/vapi/metadata/metamodel/resource/model
        # package =vapi
        service_path = get_service_path_from_service_url(service_url, base_url)
        package = service_path.split('/')[3]
        if package in package_dict:
            packages = package_dict[package]
            packages.append(service_url)
        else:
            package_dict.setdefault(package, [service_url])
    return package_dict


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


def remove_com_vmware(element_name):
    return element_name.replace('com.vmware.', '')


def populate_dicts(component_svc, enumeration_dict, structure_dict, service_dict, service_urls_map, base_url):
    components = component_svc.list()
    for component in components:
        component_data = component_svc.get(component)
        component_packages = component_data.info.packages
        for package in component_packages:
            package_info = component_packages.get(package)
            for enumeration, enumeration_info in package_info.enumerations.items():
                enumeration_name = remove_com_vmware(enumeration)
                enumeration_info.name = enumeration_name
                # enumeration_dict[enumeration] = enumeration_info
                enumeration_dict[enumeration_name] = enumeration_info
            for structure, structure_info in package_info.structures.items():
                structure_name = remove_com_vmware(structure)
                structure_info.name = structure_name
                # structure_dict[structure] = structure_info
                structure_dict[structure_name] = structure_info
                for et, et_info in structure_info.enumerations.items():
                    et_name = remove_com_vmware(et)
                    et_info.name = et_name
                    # enumeration_dict[et] = et_info
                    enumeration_dict[et_name] = et_info
            for service, service_info in package_info.services.items():
                temp_service_info = copy.deepcopy(service_info)
                for st, st_info in service_info.structures.items():
                    st_name = remove_com_vmware(st)
                    st_info.name = st_name
                    # structure_dict[st] = st_info
                    structure_dict[st_name] = st_info
                    temp_st_info = copy.deepcopy(st_info)
                    for et1, et_info1 in st_info.enumerations.items():
                        etl_name = remove_com_vmware(et1)
                        et_info1.name = etl_name
                        # enumeration_dict[et1] = et_info1
                        enumeration_dict[etl_name] = et_info1
                        temp_st_info.enumerations.pop(et1)
                        temp_st_info.enumerations[etl_name] = et_info1
                    temp_service_info.structures[st_name] = temp_st_info
                for et, et_info in service_info.enumerations.items():
                    et_name = remove_com_vmware(et)
                    et_info.name = et_name
                    enumeration_dict[et_name] = et_info
                    # enumeration_dict[et] = et_info
                    temp_service_info.enumerations.pop(et)
                    temp_service_info.enumerations[et_name] = et_info
                service_dict[service] = service_info
                service_urls_map[get_service_url_from_service_id(base_url, service)] = service


def get_service_url_from_service_id(base_url, service_id):
    replaced_string = service_id.replace('.', '/')
    return base_url + '/' + replaced_string.replace('_', '-')


def main():
    # Get user input.
    metadata_api_url, rest_navigation_url, output_dir = get_input_params()
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
    print('Connected to ' + metadata_api_url)
    component_svc = get_component_service(connector)
    populate_dicts(component_svc, enumeration_dict, structure_dict, service_dict, service_urls_map, rest_navigation_url)

    service_urls_map = get_service_urls_from_rest_navigation(rest_navigation_url)
    package_dict = categorize_service_urls_by_package_names(service_urls_map, rest_navigation_url)
    error_map = build_error_map()

    threads = []
    for package, service_urls in six.iteritems(package_dict):
        worker = threading.Thread(target=process_service_urls, args=(
            package, service_urls, output_dir, structure_dict, enumeration_dict, service_dict, service_urls_map,
            error_map, rest_navigation_url))
        worker.daemon = True
        worker.start()
        threads.append(worker)
    for worker in threads:
        worker.join()

    # api.json contains list of packages which is used by UI to dynamically populate dropdown.
    api_files = {'files': list(package_dict.keys())}
    write_json_data_to_file(output_dir + os.path.sep + 'api.json', api_files)
    stop = timeit.default_timer()
    print('Generated swagger files at ' + output_dir + ' for ' + metadata_api_url + ' in ' + str(
        stop - start) + ' seconds')


if __name__ == '__main__':
    main()
