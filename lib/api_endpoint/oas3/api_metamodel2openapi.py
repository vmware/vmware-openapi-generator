from lib import utils
from lib.api_endpoint.oas3 import api_openapi_parameter_handler as api_open_ph
from lib.api_endpoint.oas3 import api_openapi_response_handler as api_open_rh

def get_path(operation_info, http_method, url, service_name, type_dict, structure_dict, enum_dict,
             operation_id, error_map, enable_filtering):
    documentation = operation_info.documentation
    params = operation_info.params
    errors = operation_info.errors
    output = operation_info.output
    http_method = http_method.lower()
    consumes = None
    produces = None
    par_array, url = handle_request_mapping(url, http_method, service_name,
                                            operation_id, params, type_dict,
                                            structure_dict, enum_dict, enable_filtering)
    response_map = api_open_rh.populate_response_map(output,
                                         errors,
                                         error_map, type_dict, structure_dict, enum_dict, service_name, operation_id, enable_filtering) 

    path_obj = utils.build_path(service_name,
                      http_method,
                      url,
                      documentation, par_array, operation_id=operation_id,
                      responses=response_map,
                      consumes=consumes, produces=produces)
    post_process_path(path_obj)
    path = utils.add_basic_auth(path_obj)
    return path

def handle_request_mapping(url, method_type, service_name, operation_name, params_metadata,
                           type_dict, structure_svc, enum_svc, enable_filtering):
    if method_type in ('post', 'put', 'patch'):
        return process_put_post_patch_request(url, service_name, operation_name,
                                              params_metadata, type_dict, structure_svc,
                                              enum_svc, enable_filtering)
    if method_type == 'get':
        return process_get_request(url, params_metadata, type_dict,
                                   structure_svc, enum_svc, enable_filtering)
    if method_type == 'delete':
        return process_delete_request(url, params_metadata, type_dict,
                                      structure_svc, enum_svc, enable_filtering)

def process_put_post_patch_request(url, service_name, operation_name, params,
                                   type_dict, structure_svc, enum_svc, enable_filtering):
    """
    Handles http post/put/patch request.
    todo: handle query, formData and header parameters
    """
    ## Path
    path_param_list, other_param_list, new_url = utils.extract_path_parameters(params, url)
    par_array = []
    for field_info in path_param_list:
        parx = api_open_ph.convert_field_info_to_swagger_parameter('path', field_info, type_dict,
                                                       structure_svc, enum_svc, enable_filtering)
        par_array.append(parx)

    ## Body
    body_param_list, other_param_list =  utils.extract_body_parameters(other_param_list)

    if body_param_list:
        parx = api_open_ph.wrap_body_params(service_name, operation_name, body_param_list, type_dict,
                                structure_svc, enum_svc, enable_filtering)
        if parx is not None:
            par_array.append(parx)

    ## Query 
    query_param_list, other_param_list = utils.extract_query_parameters(other_param_list)
    for query_param in query_param_list:
        parx = api_open_ph.convert_field_info_to_swagger_parameter('query', query_param, type_dict,
                                                        structure_svc, enum_svc, enable_filtering)
        par_array.append(parx)

    # process query parameters
    for field_info in other_param_list:
        # See documentation of method flatten_query_param_spec to understand
        # handling of all the query parameters; filter as well as non filter
        flattened_params = api_open_ph.flatten_query_param_spec(field_info, type_dict, structure_svc, enum_svc, enable_filtering)
        if flattened_params is not None:
            par_array = par_array + flattened_params

    return par_array, new_url

def process_get_request(url, params, type_dict, structure_svc, enum_svc, enable_filtering):
    param_array = []
    path_param_list, other_params_list, new_url = utils.extract_path_parameters(params, url)

    for field_info in path_param_list:
        parameter_obj = api_open_ph.convert_field_info_to_swagger_parameter('path', field_info,
                                                                type_dict, structure_svc, enum_svc, enable_filtering)
        param_array.append(parameter_obj)

    query_param_list, other_params_list = utils.extract_query_parameters(other_params_list)
    #Query
    for query_param in query_param_list:
        parameter_obj = api_open_ph.convert_field_info_to_swagger_parameter('query', query_param,
                                                            type_dict, structure_svc, enum_svc, enable_filtering)
        param_array.append(parameter_obj)

    # process query parameters
    for field_info in other_params_list:
        # See documentation of method flatten_query_param_spec to understand
        # handling of all the query parameters; filter as well as non filter
        flattened_params = api_open_ph.flatten_query_param_spec(field_info, type_dict, structure_svc, enum_svc, enable_filtering)
        if flattened_params is not None:
            param_array = param_array + flattened_params
    return param_array, new_url

def process_delete_request(url, params, type_dict, structure_svc, enum_svc, enable_filtering):
    path_param_list, other_params, new_url = utils.extract_path_parameters(params, url)
    param_array = []
    for field_info in path_param_list:
        parx = api_open_ph.convert_field_info_to_swagger_parameter('path', field_info, type_dict,
                                                       structure_svc, enum_svc, enable_filtering)
        param_array.append(parx)
    for field_info in other_params:
        parx = api_open_ph.convert_field_info_to_swagger_parameter('query', field_info, type_dict,
                                                        structure_svc, enum_svc, enable_filtering)
        param_array.append(parx)
    return param_array, new_url

def post_process_path(path_obj):
    # Temporary fixes necessary for generated spec files.
    # Hardcoding for now as it is not available from metadata.
    if path_obj['path'] == '/com/vmware/cis/session' and path_obj['method'] == 'post':
        header_parameter = {'in': 'header', 'required': True, 'type': 'string',
                            'name': 'vmware-use-header-authn',
                            'description': 'Custom header to protect against CSRF attacks in browser based clients'}
        header_parameter['schema'] = { 'type' : 'string' }
        path_obj['parameters'] = [header_parameter]

    # Allow invoking $task operations from the api-explorer
    if path_obj['operationId'].endswith('$task'):
        path_obj['path'] = utils.add_query_param(path_obj['path'], 'vmw-task=true')
