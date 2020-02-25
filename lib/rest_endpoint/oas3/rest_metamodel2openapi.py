from lib.rest_endpoint.oas3 import rest_openapi_parameter_handler as rest_open_ph
from lib.rest_endpoint.oas3 import rest_openapi_response_handler as rest_open_rh
TAG_SEPARATOR = '/'

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
    response_map = rest_open_rh.populate_response_map(output,
                                         errors,
                                         error_map, type_dict, structure_dict, enum_dict, service_name, operation_id, enable_filtering)

    path = build_path(service_name,
                      http_method,
                      url,
                      documentation, par_array, operation_id=operation_id,
                      responses=response_map,
                      consumes=consumes, produces=produces)
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
    path_param_list, other_param_list, new_url = rest_open_ph.extract_path_parameters(params, url)
    par_array = []
    for field_info in path_param_list:
        parx = rest_open_ph.convert_field_info_to_swagger_parameter('path', field_info, type_dict,
                                                       structure_svc, enum_svc, enable_filtering)
        par_array.append(parx)

    #Body
    body_param_list = other_param_list
    
    if body_param_list:
        parx = rest_open_ph.wrap_body_params(service_name, operation_name, body_param_list, type_dict,
                                structure_svc, enum_svc, enable_filtering)
        if parx is not None:
            par_array.append(parx)

    return par_array, new_url

def process_get_request(url, params, type_dict, structure_svc, enum_svc, enable_filtering):
    param_array = []
    path_param_list, other_params_list, new_url = rest_open_ph.extract_path_parameters(params, url)
    
    for field_info in path_param_list:
        parameter_obj = rest_open_ph.convert_field_info_to_swagger_parameter('path', field_info,
                                                                type_dict, structure_svc, enum_svc, enable_filtering)
        param_array.append(parameter_obj)

    # process query parameters
    for field_info in other_params_list:
        # See documentation of method flatten_query_param_spec to understand
        # handling of all the query parameters; filter as well as non filter
        flattened_params = rest_open_ph.flatten_query_param_spec(field_info, type_dict, structure_svc, enum_svc, enable_filtering)
        if flattened_params is not None:
            param_array = param_array + flattened_params
    return param_array, new_url

def process_delete_request(url, params, type_dict, structure_svc, enum_svc, enable_filtering):
    path_param_list, other_params, new_url = rest_open_ph.extract_path_parameters(params, url)
    param_array = []
    for field_info in path_param_list:
        parx = rest_open_ph.convert_field_info_to_swagger_parameter('path', field_info, type_dict,
                                                       structure_svc, enum_svc, enable_filtering)
        param_array.append(parx)
    for field_info in other_params:
        parx = rest_open_ph.convert_field_info_to_swagger_parameter('query', field_info, type_dict, structure_svc, enum_svc, enable_filtering)
        param_array.append(parx)
    return param_array, new_url

def build_path(service_name, method, path, documentation, parameters, operation_id, responses, consumes,
               produces):
    """
    builds swagger path object
    :param service_name: name of service. ex com.vmware.vcenter.VM
    :param method: type of method. ex put, post, get, patch
    :param path: relative path to an individual endpoint
    :param documentation: api documentation
    :param parameters: input parameters for the api
    :param responses: response of the api
    :param consumes: expected media type format of api input
    :param produces: expected media type format of api output
    :return: swagger path object.
    """
    path_obj = {}
    path_obj['tags'] = tags_from_service_name(service_name)
    if method is not None:
        path_obj['method'] = method
    if path is not None:
        path_obj['path'] = path
    if documentation is not None:
        path_obj['summary'] = documentation
    if parameters is not None:
        path_obj['parameters'] = parameters
    if responses is not None:
        path_obj['responses'] = responses
    if consumes is not None:
        path_obj['consumes'] = consumes
    if produces is not None:
        path_obj['produces'] = produces
    if operation_id is not None:
        path_obj['operationId'] = operation_id
    post_process_path(path_obj)
    add_basic_auth(path_obj)
    return path_obj

def tags_from_service_name(service_name):
    """
    Generates the tags based on the service name.
    :param service_name: name of the service
    :return: a list of tags
    """
    return [TAG_SEPARATOR.join(service_name.split('.')[3:])]

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
        path_obj['path'] = add_query_param(path_obj['path'], 'vmw-task=true')
    
def add_query_param(url, param):
    """
    Rudimentary support for adding a query parameter to a url.
    Does nothing if the parameter is already there.
    :param url: the input url
    :param param: the parameter to add (in the form of key=value)
    :return: url with added param, ?param or &param at the end
    """
    pre_param_symbol = '?'
    query_index = url.find('?')
    if query_index > -1:
        if query_index == len(url):
            pre_param_symbol = ''
        elif url[query_index + 1:].find(param) > -1:
            return url
        else:
            pre_param_symbol = '&'
    return url + pre_param_symbol + param

def add_basic_auth(path_obj):
    """Add basic auth security requirement to paths requiring it."""
    if path_obj['path'] == '/com/vmware/cis/session' and path_obj['method'] == 'post':
        path_obj['security'] = [{'basic_auth': []}]