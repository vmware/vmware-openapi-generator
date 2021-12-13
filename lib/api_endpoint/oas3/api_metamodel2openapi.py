# Copyright 2020 VMware, Inc.
# SPDX-License-Identifier: MIT

from lib import utils
from lib.api_endpoint.api_metamodel2spec import ApiMetamodel2Spec
from .api_openapi_parameter_handler import ApiOpenapiParaHandler
from .api_openapi_response_handler import ApiOpenapiRespHandler

api_open_ph = ApiOpenapiParaHandler()
api_open_rh = ApiOpenapiRespHandler()


class ApiMetamodel2Openapi(ApiMetamodel2Spec):
    def get_path(
            self,
            operation_info,
            http_method,
            url,
            service_name,
            type_dict,
            structure_dict,
            enum_dict,
            operation_id,
            http_error_map,
            show_unreleased_apis):
        documentation = operation_info.documentation
        op_metadata = operation_info.metadata
        method_info = op_metadata[http_method]
        content_type = method_info.elements["consumes"].string_value if "consumes" in method_info.elements else None

        params = operation_info.params
        errors = operation_info.errors
        output = operation_info.output
        http_method = http_method.lower()
        par_array, url = self.handle_request_mapping(url, http_method, service_name,
                                                     operation_id, params, content_type, type_dict,
                                                     structure_dict, enum_dict, show_unreleased_apis, api_open_ph)
        response_map = api_open_rh.populate_response_map(
            output,
            errors,
            http_error_map,
            type_dict,
            structure_dict,
            enum_dict,
            service_name,
            operation_id,
            op_metadata,
            show_unreleased_apis)

        path_obj = utils.build_path(
            service_name,
            http_method,
            url,
            documentation,
            par_array,
            operation_id=operation_id,
            responses=response_map)

        utils.create_req_body_from_params_list(path_obj)
        self.post_process_path(path_obj)
        path = utils.add_basic_auth(path_obj)
        return path
   
    def post_process_path(self, path_obj):
        # Temporary fixes necessary for generated spec files.
        # Hardcoding for now as it is not available from metadata.
        if path_obj['path'] == '/com/vmware/cis/session' and path_obj['method'] == 'post':
            header_parameter = {
                'in': 'header',
                'required': True,
                'type': 'string',
                'name': 'vmware-use-header-authn',
                'description': 'Custom header to protect against CSRF attacks in browser based clients'}
            header_parameter['schema'] = {'type': 'string'}
            path_obj['parameters'] = [header_parameter]

        # Allow invoking $task operations from the api-explorer
        if path_obj['operationId'].endswith('$task'):
            path_obj['path'] = utils.add_query_param(
                path_obj['path'], 'vmw-task=true')
