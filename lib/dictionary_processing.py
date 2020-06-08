import os

from lib import utils
from lib import blacklist_utils
from lib.rest_endpoint.rest_navigation_handler import RestNavigationHandler


class ServiceType:
    SLASH_REST = 1
    SLASH_API = 2
    SLASH_REST_AND_API = 3

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
        deprecate_rest=False):

    package_dict_api = {}
    package_dict = {}
    package_dict_deprecated = {}
    '''
    The replacement navigation map is used when DEPRECATED specification is issued (@VERB + an old annotation standard)
    It contains mappings to url paths, served as replacements. The structure of the map is the following: 
    service -> operation -> method -> raplacement path
    '''
    replacement_dict = {}

    rest_services = {}
    for k, v in service_urls_map.items():
        rest_services.update({
            v: k
        })

    for service in service_dict:
        service_type, path_list = get_paths_inside_metamodel(service,
                                                             service_dict,
                                                             deprecate_rest,
                                                             replacement_dict,
                                                             rest_services.get(service, None),
                                                             rest_navigation_handler)
        if (service_type in [ServiceType.SLASH_API, ServiceType.SLASH_REST_AND_API]) and not blacklist_utils.is_blacklisted_for_api(service):
            for path in path_list:
                service_urls_map[path] = (service, '/api')
                package_name = path.split('/')[1]
                pack_arr = package_dict_api.get(package_name, [])
                if pack_arr == []:
                    package_dict_api[package_name] = pack_arr
                pack_arr.append(path)
        elif service_type == ServiceType.SLASH_REST and not blacklist_utils.is_blacklisted_for_rest(service):
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
        if service_type == ServiceType.SLASH_REST_AND_API and not blacklist_utils.is_blacklisted_for_rest(service):
            service_url = rest_services.get(service, None)
            if service_url is not None:
                service_path = get_service_path_from_service_url(
                    service_url, rest_navigation_handler.get_rest_navigation_url())
                service_urls_map[service_path] = (service, '/deprecated')
                package = service_path.split('/')[3]
                if package in package_dict_deprecated:
                    packages = package_dict_deprecated[package]
                    packages.append(service_path)
                else:
                    package_dict_deprecated.setdefault(package, [service_path])
            else:
                print("Service does not belong to either /api or /rest ", service)

    return package_dict_api, package_dict, package_dict_deprecated, replacement_dict


#TODO the overly complicated method below along with add_service_urls_using_metamodel should be refactored
# They should be separated in different strategies, for each api type - /rest, /api and deprecated (/rest and /api)
def get_paths_inside_metamodel(service, service_dict, deprecate_rest=False, replacement_dict={}, service_url=None, rest_navigation_handler=None):
    path_list = set()
    is_rest_api_existing = False
    is_in_rest_navigation = False
    is_rest_navigation_checked = False

    for operation_id in service_dict[service].operations.keys():
        for request in service_dict[service].operations[operation_id].metadata.keys(
        ):
            if request.lower() in ('post', 'put', 'patch', 'get', 'delete'):
                path = service_dict[service].operations[operation_id].metadata[request].elements['path'].string_value
                path_list.add(path)

                # If already found in navigation, no need to check for request mapping
                if not is_in_rest_navigation:
                    is_rest_api_existing = check_for_request_mapping_replacement(service_dict[service], operation_id)

                if not is_rest_api_existing and not is_rest_navigation_checked:
                    is_rest_api_existing = check_for_rest_navigation_replacement(service_url, rest_navigation_handler)
                    # Add all operations and methods to replacements if it is apparent in rest_navigation
                    is_in_rest_navigation = is_rest_api_existing
                    is_rest_navigation_checked = True

                if is_rest_api_existing:
                    add_replacement_path(service, operation_id, request.lower(), path, replacement_dict)
                    # If a newer version of the api is included - remove it unless deprecation is on
                    if not deprecate_rest:
                        path_list.remove(path)

    if path_list == set():
        return ServiceType.SLASH_REST, []

    if is_rest_api_existing:
        return ServiceType.SLASH_REST_AND_API, sorted(list(path_list))

    return ServiceType.SLASH_API, sorted(list(path_list))


def check_for_request_mapping_replacement(service, operation_id):
    # Check whether the service contains both @RequestMapping and @Verb annotations
    if 'RequestMapping' in service.operations[operation_id].metadata.keys():
        return True
    return False


def check_for_rest_navigation_replacement(service_url, rest_navigation_handler):
    if service_url is not None and rest_navigation_handler is not None:
        # Check whether the service is apparent in the rest navigation - has 6.0
        service_operations = rest_navigation_handler.get_service_operations(service_url)
        if service_operations is not None:
            return True
    return False


def get_service_path_from_service_url(service_url, base_url):
    if not service_url.startswith(base_url):
        return service_url

    return service_url[len(base_url):]


def add_replacement_path(service, operation_id, method, path, replacement_dict):
    if service not in replacement_dict:
        replacement_dict[service] = {operation_id: (method, path)}
    else:
        replacement_dict[service][operation_id] = (method, path)
