from lib import utils, authentication_metadata_processing
from lib.api_endpoint.api_metamodel2spec import ApiMetamodel2Spec
from .api_swagger_parameter_handler import ApiSwaggerParaHandler
from .api_swagger_response_handler import ApiSwaggerRespHandler

api_swagg_ph = ApiSwaggerParaHandler()
api_swagg_rh = ApiSwaggerRespHandler()


class ApiMetamodel2Swagger(ApiMetamodel2Spec):
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
        params = operation_info.params
        errors = operation_info.errors
        output = operation_info.output
        http_method = http_method.lower()
        par_array, url = self.handle_request_mapping(url, http_method, service_name,
                                                     operation_id, params, type_dict,
                                                     structure_dict, enum_dict, show_unreleased_apis, api_swagg_ph)
        response_map = api_swagg_rh.populate_response_map(
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
            header_parameter['type'] = 'string'
            path_obj['parameters'] = [header_parameter]

        # Allow invoking $task operations from the api-explorer
        if path_obj['operationId'].endswith('$task'):
            path_obj['path'] = utils.add_query_param(
                path_obj['path'], 'vmw-task=true')

    def decorate_path_with_security(self, path_obj, scheme_set):
        if authentication_metadata_processing.no_authentication_scheme in scheme_set:
            path_obj["security"] = []
        elif authentication_metadata_processing.basic_auth_scheme in scheme_set:
            path_obj["security"] = [{"basic_auth": []}]