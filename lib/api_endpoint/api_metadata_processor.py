import os
import threading

import six
from lib import utils
from lib.metadata_processor import MetadataProcessor
from .oas3.api_metamodel2openapi import ApiMetamodel2Openapi
from .swagger2.api_metamodel2swagger import ApiMetamodel2Swagger


openapi = ApiMetamodel2Openapi()
swagg = ApiMetamodel2Swagger()


class ApiMetadataProcessor(MetadataProcessor):

    def __init__(self):
        pass

    def get_path_and_type_dicts(
            self,
            package_name,
            service_urls,
            structure_dict,
            enum_dict,
            service_dict,
            service_url_dict,
            http_error_map,
            show_unreleased_apis,
            spec,
            auth_navigator):

        print('processing package ' + package_name + os.linesep)
        type_dict = {}
        path_list = []
        for service_url in service_urls:
            service_name, service_end_point = service_url_dict.get(
                service_url, None)
            service_info = service_dict.get(service_name, None)
            if service_info is None:
                continue
            if (not show_unreleased_apis) and utils.is_filtered(service_info.metadata):
                continue
            for operation_id, operation_info in service_info.operations.items():

                method, url = self.api_get_url_and_method(
                    operation_info.metadata)
                if method is None or url is None:
                    continue

                # check for query parameters
                if 'params' in operation_info.metadata[method].elements:
                    element_value = operation_info.metadata[method].elements['params']
                    params = "&".join(element_value.list_value)
                    url = url + '?' + params

                if spec == '2':
                    path = swagg.get_path(
                        operation_info,
                        method,
                        url,
                        service_name,
                        type_dict,
                        structure_dict,
                        enum_dict,
                        operation_id,
                        http_error_map,
                        show_unreleased_apis)
                    scheme_set = auth_navigator.find_schemes_set(operation_id, service_name, package_name)
                    if scheme_set is not None and len(scheme_set) != 0:
                        swagg.decorate_path_with_security(path, scheme_set)
                if spec == '3':
                    path = openapi.get_path(
                        operation_info,
                        method,
                        url,
                        service_name,
                        type_dict,
                        structure_dict,
                        enum_dict,
                        operation_id,
                        http_error_map,
                        show_unreleased_apis)

                path_list.append(path)
            continue

        path_dict = self.convert_path_list_to_path_map(path_list)
        self.cleanup(path_dict=path_dict, type_dict=type_dict)
        return path_dict, type_dict

    def api_get_url_and_method(self, metadata):
        for method in metadata.keys():
            if method in ['POST', 'GET', 'DELETE', 'PUT', 'PATCH']:
                url_path = metadata[method].elements["path"].string_value
                url_path = "/api" + url_path
                return method, url_path
        return None, None
