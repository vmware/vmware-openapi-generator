import json
import os
import requests
import six
from six.moves import http_client
from lib import utils
from enum import Enum

from lib.rest_endpoint.rest_navigation_handler import RestNavigationHandler


class ServiceType:
    REST = 1
    API = 2
    MIXED = 3

def populate_dicts(
        component_svc,
        enumeration_dict,
        structure_dict,
        service_dict,
        service_urls_map,
        base_url,
        generate_metamodel):
    components = component_svc.list()
    for component in components:
        component_data = component_svc.get(component)
        if generate_metamodel:
            if not os.path.exists('metamodel'):
                os.mkdir('metamodel')
            utils.write_json_data_to_file(
                'metamodel/' + component + '.json',
                objectTodict(component_data))
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
                service_urls_map[get_service_url_from_service_id(
                    base_url, service)] = service
                for structure_name, structure_info in service_info.structures.items():
                    structure_dict[structure_name] = structure_info
                    for et1, et_info1 in structure_info.enumerations.items():
                        enumeration_dict[et1] = et_info1
                for enum_name, enum_info in service_info.enumerations.items():
                    enumeration_dict[enum_name] = enum_info


def objectTodict(obj):
    objtype = type(obj)
    if objtype is int or objtype is str or objtype is float or isinstance(
            None, objtype) or objtype is bool:
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


def get_service_url_from_service_id(base_url, service_id):
    replaced_string = service_id.replace('.', '/')
    return base_url + '/' + replaced_string.replace('_', '-')


def get_service_urls_from_rest_navigation(rest_navigation_url, verify):
    component_services_urls = get_component_services_urls(
        rest_navigation_url, verify)
    return get_all_services_urls(component_services_urls, verify)


def get_component_services_urls(cloudvm_url, verify):
    components_url = utils.get_json(cloudvm_url, verify)['components']['href']
    components = utils.get_json(components_url, verify)
    return [component['services']['href'] for component in components]


def get_all_services_urls(components_urls, verify):
    service_url_dict = {}
    for url in components_urls:
        services = utils.get_json(url, verify)
        for service in services:
            service_url_dict[service['href']] = service['name']
    return service_url_dict


def add_service_urls_using_metamodel(
        service_urls_map,
        service_dict,
        rest_navigation_handler: RestNavigationHandler,
        mixed=False):

    package_dict_api = {}
    package_dict = {}
    package_dict_deprecated = {}
    '''
    The replacement navigation map is used when MIXED specification is issued (@VERB + an old annotation standard)
    It contains mappings to url paths, served as replacements. The structure of the map is the following: 
    service -> operation -> method -> raplacement path
    '''
    replacement_map = {}

    rest_services = {}
    for k, v in service_urls_map.items():
        rest_services.update({
            v: k
        })

    for service in service_dict:
        service_type, path_list = get_paths_inside_metamodel(service, service_dict, mixed, replacement_map, rest_services.get(service, None), rest_navigation_handler)
        if service_type == ServiceType.API or service_type == ServiceType.MIXED:
            for path in path_list:
                service_urls_map[path] = (service, '/api')
                package_name = path.split('/')[1]
                pack_arr = package_dict_api.get(package_name, [])
                if pack_arr == []:
                    package_dict_api[package_name] = pack_arr
                pack_arr.append(path)
        elif service_type == ServiceType.REST:
            service_url = rest_services.get(service, None)
            if service_url is not None:
                service_path = get_service_path_from_service_url(
                    service_url, rest_navigation_handler.get_rest_navigation_url())
                service_urls_map[service_path] = (service, '/rest')
                package = service_path.split('/')[3]
                if package in package_dict:
                    packages = package_dict[package]
                    packages.append(service_path)
                else:
                    package_dict.setdefault(package, [service_path])
            else:
                print("Service does not belong to either /api or /rest ", service)
        if service_type == ServiceType.MIXED:
            service_url = rest_services.get(service, None)
            if service_url is not None:
                service_path = get_service_path_from_service_url(
                    service_url, rest_navigation_handler.get_rest_navigation_url())
                service_urls_map[service_path] = (service, '/mixed')
                package = service_path.split('/')[3]
                if package in package_dict_deprecated:
                    packages = package_dict_deprecated[package]
                    packages.append(service_path)
                else:
                    package_dict_deprecated.setdefault(package, [service_path])
            else:
                print("Service does not belong to either /api or /rest ", service)
    if mixed:
        return package_dict_api, package_dict, package_dict_deprecated, replacement_map

    return package_dict_api, package_dict



def get_paths_inside_metamodel(service, service_dict, mixed=False, replacement_map={}, service_url=None, rest_navigation_handler=None):
    path_list = set()
    is_mixed = False
    for operation_id in service_dict[service].operations.keys():
        for request in service_dict[service].operations[operation_id].metadata.keys(
        ):
            if request.lower() in ('post', 'put', 'patch', 'get', 'delete'):
                path = service_dict[service].operations[operation_id].metadata[request].elements['path'].string_value
                path_list.add(path)

                # Check whether the service contains both @RequestMapping and @Verb annotations
                if mixed and 'RequestMapping' in service_dict[service].operations[operation_id].metadata.keys():
                    is_mixed = True
                    add_replcament_path(service, operation_id, request.lower(), path, replacement_map)
                elif mixed and service_url is not None and rest_navigation_handler is not None:
                    # Check whether the service is apparent in the rest navigation - has 6.0
                    service_operations = rest_navigation_handler.get_service_operations(service_url)
                    if service_operations is not None:
                        is_mixed = True
                        add_replcament_path(service, operation_id, request.lower(), path, replacement_map)

    if path_list == set():
        return ServiceType.REST, []

    if is_mixed:
        return ServiceType.MIXED, sorted(list(path_list))

    return ServiceType.API, sorted(list(path_list))


def get_service_path_from_service_url(service_url, base_url):
    if not service_url.startswith(base_url):
        return service_url

    return service_url[len(base_url):]

def add_replcament_path(service, operation_id, method, path, replacement_map):
    if service not in replacement_map:
        replacement_map[service] = {operation_id: {method: path}}
    elif operation_id not in replacement_map[service]:
        replacement_map[service][operation_id] = {method: path}
    else:
        replacement_map[service][operation_id][method] = path