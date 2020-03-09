from lib import utils
from lib.api_endpoint.api_metamodel2spec import apiMetamodel2Spec
from .api_swagger_parameter_handler import apiSwaggerParaHandler  
from .api_swagger_response_handler import apiSwaggerRespHandler   

api_swagg_ph = apiSwaggerParaHandler()
api_swagg_rh = apiSwaggerRespHandler()

class apiMetamodel2Swagger(apiMetamodel2Spec):
    def get_path(self, operation_info, http_method, url, service_name, type_dict, structure_dict, enum_dict,
                operation_id, error_map, enable_filtering):
        documentation = operation_info.documentation
        params = operation_info.params 
        errors = operation_info.errors
        output = operation_info.output
        http_method = http_method.lower()
        consumes_json = self.find_consumes(http_method)
        produces = None
        par_array, url = self.handle_request_mapping(url, http_method, service_name,
                                                operation_id, params, type_dict,
                                                structure_dict, enum_dict, enable_filtering, api_swagg_ph)
        response_map = api_swagg_rh.populate_response_map(output,
                                            errors,
                                            error_map, type_dict, structure_dict, enum_dict, service_name, operation_id, enable_filtering)

        path_obj = utils.build_path(service_name,
                        http_method,
                        url,
                        documentation, par_array, operation_id=operation_id,
                        responses=response_map,
                        consumes=consumes_json, produces=produces)
        self.post_process_path(path_obj)
        path = utils.add_basic_auth(path_obj)
        return path

    def find_consumes(self, method_type):
        """
        Determine mediaType for input parameters in request body.
        """
        if method_type in ('get', 'delete'):
            return None
        return ['application/json']

    def post_process_path(self, path_obj):
        # Temporary fixes necessary for generated spec files.
        # Hardcoding for now as it is not available from metadata.
        if path_obj['path'] == '/com/vmware/cis/session' and path_obj['method'] == 'post':
            header_parameter = {'in': 'header', 'required': True, 'type': 'string',
                                'name': 'vmware-use-header-authn',
                                'description': 'Custom header to protect against CSRF attacks in browser based clients'}
            header_parameter['type'] = 'string'
            path_obj['parameters'] = [header_parameter]

        # Allow invoking $task operations from the api-explorer
        if path_obj['operationId'].endswith('$task'):
            path_obj['path'] = utils.add_query_param(path_obj['path'], 'vmw-task=true')