import requests
from six.moves import http_client
from lib.rest_endpoint.swagger2.rest_swagger_type_handler import typeHandler

def populate_response_map(output, errors, error_map, type_dict, structure_svc, enum_svc, service_id, operation_id, enable_filtering):

    response_map = {}
    ref_path = "#/definitions/"
    success_response = {'description': output.documentation}
    schema = {}
    tpHandler = typeHandler()
    tpHandler.visit_type_category(output.type, schema, type_dict, structure_svc, enum_svc, ref_path, enable_filtering)
    # if type of schema is void, don't include it.
    # this prevents showing response as void in swagger-ui
    if schema is not None:
        if not ('type' in schema and schema['type'] == 'void'):
            # Handling Value wrappers for /rest and /api
            resp = {
                'type': 'object',
                'properties': {'value': schema},
                'required': ['value']
            }
            if operation_id == 'get':
                type_name = service_id
            else:
                type_name = service_id + '.' + operation_id
            
            type_name = type_name + '_result'

            if type_name not in type_dict:
                type_dict[type_name] = resp

            success_response['schema'] = {"$ref": ref_path + type_name}

    # success response is not mapped through metamodel.
    # hardcode it for now.
    response_map[requests.codes.ok] = success_response

    for error in errors:
        status_code = error_map.get(error.structure_id, http_client.INTERNAL_SERVER_ERROR)
        tpHandler.check_type('com.vmware.vapi.structure', error.structure_id, type_dict, structure_svc, enum_svc, ref_path, enable_filtering)
        schema_obj = {'type': 'object', 'properties': {'type': {'type': 'string'},
                                                        'value': {'$ref': ref_path + error.structure_id}}}
        type_dict[error.structure_id + '_error'] = schema_obj
        response_obj = {'description': error.documentation, 'schema': {'$ref': ref_path
                                                                               + error.structure_id + '_error'}}
        response_map[status_code] = response_obj

    return response_map