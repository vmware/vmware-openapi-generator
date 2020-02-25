import json
import os
import requests
import six
from six.moves import http_client
from lib import utils

def populate_dicts(component_svc, enumeration_dict, structure_dict, service_dict, service_urls_map, base_url, generate_metamodel):
    components = component_svc.list()
    for component in components:
        component_data = component_svc.get(component)
        if generate_metamodel:
            if not os.path.exists('metamodel'):
                os.mkdir('metamodel')
            utils.write_json_data_to_file('metamodel/'+component+'.json', objectTodict(component_data))
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

def get_service_url_from_service_id(base_url, service_id):
    replaced_string = service_id.replace('.', '/')
    return base_url + '/' + replaced_string.replace('_', '-')

def get_service_urls_from_rest_navigation(rest_navigation_url, verify):
    component_services_urls = get_component_services_urls(rest_navigation_url, verify)
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

def add_service_urls_using_metamodel(service_urls_map, service_dict, rest_navigation_url):

    package_dict_api = {}
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
                pack_arr = package_dict_api.get(package_name, [])
                if pack_arr == []:
                    package_dict_api[package_name] = pack_arr
                pack_arr.append(path)
        else:
            service_url = rest_services.get(service, None)
            if service_url != None:
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
    return package_dict_api, package_dict

def get_paths_inside_metamodel(service, service_dict):
    path_list = set()
    for operation_id in service_dict[service].operations.keys():
        for request in service_dict[service].operations[operation_id].metadata.keys():
            if request.lower() in ('post', 'put', 'patch', 'get', 'delete'):
                path_list.add(service_dict[service].operations[operation_id].metadata[request].elements['path'].string_value)
    
    if path_list == set():
        return False, []

    return True, sorted(list(path_list))

def get_service_path_from_service_url(service_url, base_url):
    if not service_url.startswith(base_url):
        return service_url

    return service_url[len(base_url):]