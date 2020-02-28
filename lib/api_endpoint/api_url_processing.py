import os
import six
from lib import utils
from lib.endpoint_processing import urlProcessing
from lib.api_endpoint.oas3 import api_metamodel2openapi as openapi
from lib.api_endpoint.swagger2 import api_metamodel2swagger as swagg
from lib.api_endpoint.oas3.api_openapi_final_path_processing import apiOpenapiPathProcessing
from lib.api_endpoint.swagger2.api_swagger_final_path_processing import apiSwaggerPathProcessing

api_openapi_fpp = apiOpenapiPathProcessing()
api_swagg_fpp = apiSwaggerPathProcessing()

class apiUrlProcessing(urlProcessing):

    def __init__(self):
        pass

    def process_service_urls(self,package_name, service_urls, output_dir, structure_dict, enum_dict,
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
            for operation_id, operation_info in service_info.operations.items():
                method, url = self.api_get_url_and_method(operation_info.metadata)

                # check for query parameters
                if 'params' in operation_info.metadata[method].elements:
                    element_value = operation_info.metadata[method].elements['params']
                    params="&".join(element_value.list_value)
                    url = url + '?' + params
                    
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
                url, method = super().find_url(service_operation['links'])
                url = super().get_service_path_from_service_url(url, rest_navigation_url)
                operation_info = service_info.operations.get(operation_id)

                if spec == '2':
                    path = swagg.get_path(operation_info, method, url, service_name, type_dict, structure_dict, enum_dict,
                                    operation_id, error_map, enable_filtering)
                if spec == '3':
                    path = openapi.get_path(operation_info, method, url, service_name, type_dict, structure_dict, enum_dict,
                                    operation_id, error_map, enable_filtering)

                path_list.append(path)
        path_dict = super().convert_path_list_to_path_map(path_list)
        super().cleanup(path_dict=path_dict, type_dict=type_dict)

        if spec == '2':
            api_swagg_fpp.process_output(path_dict, type_dict, output_dir, package_name, gen_unique_op_id)
        if spec == '3':
            api_openapi_fpp.process_output(path_dict, type_dict, output_dir, package_name, gen_unique_op_id)

    def api_get_url_and_method(self,metadata):
        for method in metadata.keys():
            if method in ['POST', 'GET', 'DELETE', 'PUT', 'PATCH']: 
                url_path = metadata[method].elements["path"].string_value
                return method, url_path

