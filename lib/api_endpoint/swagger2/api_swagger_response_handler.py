import requests
from six.moves import http_client
from lib.api_endpoint.api_type_handler import ApiTypeHandler


class ApiSwaggerRespHandler():

    def populate_response_map(
            self,
            output,
            errors,
            http_error_map,
            type_dict,
            structure_svc,
            enum_svc,
            service_id,
            operation_id,
            op_metadata,
            enable_filtering):

        response_map = {}
        ref_path = "#/definitions/"
        success_response = {'description': output.documentation}
        schema = {}
        tpHandler = ApiTypeHandler()
        tpHandler.visit_type_category(
            output.type,
            schema,
            type_dict,
            structure_svc,
            enum_svc,
            ref_path,
            enable_filtering)
        # if type of schema is void, don't include it.
        # this prevents showing response as void in swagger-ui
        if schema is not None:
            if not ('type' in schema and schema['type'] == 'void'):
                resp = schema
                success_response['schema'] = resp
        # success response is not mapped through metamodel.
        # hardcode it for now.
        success_response_code = requests.codes.ok
        if 'Response' in op_metadata and op_metadata['Response'] is not None:
            success_response_code = int(op_metadata['Response'].elements['code'].string_value)
        response_map[success_response_code] = success_response

        for error in errors:
            status_code = http_error_map.error_api_map.get(
                error.structure_id,
                http_client.INTERNAL_SERVER_ERROR)
            tpHandler.check_type(
                'com.vmware.vapi.structure',
                error.structure_id,
                type_dict,
                structure_svc,
                enum_svc,
                ref_path,
                enable_filtering)
            response_obj = {
                'description': error.documentation, 'schema': {
                    '$ref': ref_path + error.structure_id}}

            response_map[status_code] = response_obj
        return response_map
