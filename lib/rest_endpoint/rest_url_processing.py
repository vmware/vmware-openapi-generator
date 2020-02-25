import os
import six
from lib import utils
from lib.rest_endpoint.oas3 import rest_metamodel2openapi as openapi
from lib.rest_endpoint.swagger2 import rest_metamodel2swagger as swagg
from lib.rest_endpoint.oas3 import rest_openapi_final_path_processing as rest_openapi_fpp
from lib.rest_endpoint.swagger2 import rest_swagger_final_path_processing as rest_swagg_fpp

def process_service_urls(package_name, service_urls, output_dir, structure_dict, enum_dict,
                         service_dict, service_url_dict, error_map, rest_navigation_url, enable_filtering
                         , spec, gen_unique_op_id):

    print('processing package ' + package_name + os.linesep)
    type_dict = {}
    path_list = []
    for service_url in service_urls:
        service_name, service_end_point = service_url_dict.get(service_url, None)
        service_info = service_dict.get(service_name, None)
        if service_info is None:
            continue
        if utils.is_filtered(service_info.metadata, enable_filtering):
            continue
        if contains_rm_annotation(service_info):
            for operation in service_info.operations.values():
                url, method = find_url_method(operation)
                operation_id = operation.name
                op_metadata = service_info.operations[operation_id].metadata
                if utils.is_filtered(op_metadata, enable_filtering):
                    continue
                operation_info = service_info.operations.get(operation_id)

                if spec == '2':
                    path = swagg.get_path(operation_info, method, url, service_name, type_dict, structure_dict, enum_dict,
                                operation_id, error_map, enable_filtering)
                if spec == '3':
                    path = openapi.get_path(operation_info, method, url, service_name, type_dict, structure_dict, enum_dict,
                                operation_id, error_map, enable_filtering)

                path_list.append(path)
            continue
        # use rest navigation service to get the REST mappings for a service.
        service_operations = utils.get_json(rest_navigation_url + service_url + '?~method=OPTIONS', False)
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
            if utils.is_filtered(op_metadata, enable_filtering):
                continue
            url, method = find_url(service_operation['links'])
            url = get_service_path_from_service_url(url, rest_navigation_url)
            operation_info = service_info.operations.get(operation_id)

            if spec == '2':
                path = swagg.get_path(operation_info, method, url, service_name, type_dict, structure_dict, enum_dict,
                                operation_id, error_map, enable_filtering)
            if spec == '3':
                path = openapi.get_path(operation_info, method, url, service_name, type_dict, structure_dict, enum_dict,
                                operation_id, error_map, enable_filtering)

            path_list.append(path)
    path_dict = convert_path_list_to_path_map(path_list)
    cleanup(path_dict=path_dict, type_dict=type_dict)
    if spec == '2':
        rest_swagg_fpp.process_output(path_dict, type_dict, output_dir, package_name, gen_unique_op_id)    
    if spec== '3':
       rest_openapi_fpp.process_output(path_dict, type_dict, output_dir, package_name, gen_unique_op_id)     

def contains_rm_annotation(service_info):
    for operation in service_info.operations.values():
        if 'RequestMapping' not in operation.metadata:
            return False
    return True

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

def get_service_path_from_service_url(service_url, base_url):
    if not service_url.startswith(base_url):
        return service_url
    return service_url[len(base_url):]

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