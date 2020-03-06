import os
import six
from lib import utils
from lib.url_processing import urlProcessing
from lib.rest_endpoint.oas3.rest_metamodel2openapi import restMetamodel2Openapi
from lib.rest_endpoint.swagger2.rest_metamodel2swagger import restMetamodel2Swagger
from lib.rest_endpoint.oas3.rest_openapi_final_path_processing import restOpenapiPathProcessing
from lib.rest_endpoint.swagger2.rest_swagger_final_path_processing import restSwaggerPathProcessing

swagg = restMetamodel2Swagger()
openapi = restMetamodel2Openapi()
rest_openapi_fpp = restOpenapiPathProcessing()
rest_swagg_fpp = restSwaggerPathProcessing()

class restUrlProcessing(urlProcessing):
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
            if self.contains_rm_annotation(service_info):
                for operation in service_info.operations.values():
                    url, method = self.find_url_method(operation)
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
                url, method = self.find_url(service_operation['links'])
                url = self.get_service_path_from_service_url(url, rest_navigation_url)
                operation_info = service_info.operations.get(operation_id)

                if spec == '2':
                    path = swagg.get_path(operation_info, method, url, service_name, type_dict, structure_dict, enum_dict,
                                    operation_id, error_map, enable_filtering)
                if spec == '3':
                    path = openapi.get_path(operation_info, method, url, service_name, type_dict, structure_dict, enum_dict,
                                    operation_id, error_map, enable_filtering)

                path_list.append(path)
        path_dict = self.convert_path_list_to_path_map(path_list)
        self.cleanup(path_dict=path_dict, type_dict=type_dict)
        if spec == '2':
            rest_swagg_fpp.process_output(path_dict, type_dict, output_dir, package_name, gen_unique_op_id)    
        if spec== '3':
            rest_openapi_fpp.process_output(path_dict, type_dict, output_dir, package_name, gen_unique_op_id)     

    def contains_rm_annotation(self,service_info):
        for operation in service_info.operations.values():
            if 'RequestMapping' not in operation.metadata:
                return False
        return True

    def find_url_method(self,opinfo):
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
                url = self.find_string_element_value(element_value)
            if 'method' in element_map.elements:
                element_value = element_map.elements['method']
                method = self.find_string_element_value(element_value)
            if 'params' in element_map.elements:
                element_value = element_map.elements['params']
                params = self.find_string_element_value(element_value)
        if params is not None:
            url = url + '?' + params
        return url, method

    def find_string_element_value(self,element_value):
        """
        if input parameter is a path variable, this method
        determines name of the path variable.
        """
        if element_value is dict:
            if element_value['type'] == 'STRING':
                return element_value['string_value']
        else:
            return element_value.string_value

