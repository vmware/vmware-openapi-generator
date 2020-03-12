import re
import six
from lib import utils
from lib.api_endpoint.api_type_handler import ApiTypeHandler


class ApiOpenapiParaHandler():

    def convert_field_info_to_swagger_parameter(
            self,
            param_type,
            input_parameter_obj,
            type_dict,
            structure_svc,
            enum_svc,
            enable_filtering):
        """
        Converts metamodel fieldinfo to swagger parameter.
        """
        parameter_obj = {}
        ref_path = "#/components/schemas/"
        tpHandler = ApiTypeHandler()
        tpHandler.visit_type_category(
            input_parameter_obj.type,
            parameter_obj,
            type_dict,
            structure_svc,
            enum_svc,
            ref_path,
            enable_filtering)
        if 'required' not in parameter_obj:
            parameter_obj['required'] = True
        parameter_obj['in'] = param_type
        parameter_obj['name'] = input_parameter_obj.name
        parameter_obj['description'] = input_parameter_obj.documentation
        # $ref should be encapsulated in 'schema' instead of parameter. -> this throws swagger validation error
        # hence another method is to to get data in $ref in parameter_obj
        # itself
        if '$ref' in parameter_obj:
            type_obj = type_dict[parameter_obj['$ref'][len(ref_path):]]
            description = parameter_obj['description']
            if 'description' in type_obj:
                description = ""
                description = "{ 1. " + type_obj['description'] + \
                    " }, { 2. " + parameter_obj['description'] + " }"
            parameter_obj.update(type_obj)
            parameter_obj['description'] = description
            del parameter_obj['$ref']

        if 'type' in parameter_obj:
            temp_schema = {'type': parameter_obj['type']}
            parameter_obj['schema'] = temp_schema
            del parameter_obj['type']

        return parameter_obj

    def wrap_body_params(
            self,
            service_name,
            operation_name,
            body_param_list,
            type_dict,
            structure_svc,
            enum_svc,
            enable_filtering):
        """
        Creates a  json object wrapper around request body parameters. parameter names are used as keys and the
        parameters as values.
        For instance, datacenter create operation takes CreateSpec whose parameter name is spec.
        This method creates a json wrapper object
        datacenter.create {
        'spec' : {spec obj representation  }
        }
        """
        # todo:
        # not unique enough. make it unique
        wrapper_name = service_name + '_' + operation_name
        body_obj = {}
        properties_obj = {}
        required = []
        ref_path = "#/components/schemas/"
        tpHandler = ApiTypeHandler()
        for param in body_param_list:
            parameter_obj = {}
            tpHandler.visit_type_category(
                param.type,
                parameter_obj,
                type_dict,
                structure_svc,
                enum_svc,
                ref_path,
                enable_filtering)
            parameter_obj['description'] = param.documentation
            body_obj.update(parameter_obj)

        if 'requestBodies' not in type_dict:
            type_dict['requestBodies'] = {}
        type_dict['requestBodies'][wrapper_name] = {
            'content': {
                'application/json': {
                    'schema': {
                        '$ref': ref_path + wrapper_name
                    }
                }
            }
        }
        type_dict[wrapper_name] = body_obj
        parameter_obj = {'$ref': "#/components/requestBodies/" + wrapper_name}

        return parameter_obj

    def flatten_query_param_spec(
            self,
            query_param_info,
            type_dict,
            structure_svc,
            enum_svc,
            enable_filtering):
        """
        Flattens query parameters specs.
        1. Create a query parameter for every field in spec.
            Example 1:
                consider datacenter get which accepts optional filterspec.
                Optional<Datacenter.FilterSpec> filter)
                The method would convert the filterspec to 3 separate query parameters
                filter.datacenters, filter.names and filter.folders.
            Example 2:
                consider /vcenter/deployment/install/initial-config/remote-psc/thumbprint get
                which accepts parameter
                vcenter.deployment.install.initial_config.remote_psc.thumbprint.remote_spec.
                The two members defined under remote_spec
                address and https_port are converted to two separate query parameters
                address(required) and https_port(optional).
        2. The field info is simple type. i.e the type is string, integer
            then it is converted it to swagger parameter.
            Example:
                consider /com/vmware/content/library/item get
                which accepts parameter 'library_id'. The field is converted
                to library_id query parameter.
        3. This field has references to a spec but the spec is not
            a complex type and does not have property 'properties'.
            i.e the type is string, integer. The members defined under the spec are
            converted to query parameter.
            Example:
                consider /appliance/update/pending get which accepts two parameter
                'source_type' and url. Where source_type is defined in the spec
                'appliance.update.pending.source_type' and field url
                is of type string.
                The fields 'source_type' and 'url' are converted to query parameter
                of type string.
        """
        prop_array = []
        parameter_obj = {}
        ref_path = "#/components/schemas/"
        tpHandler = ApiTypeHandler()
        tpHandler.visit_type_category(
            query_param_info.type,
            parameter_obj,
            type_dict,
            structure_svc,
            enum_svc,
            ref_path,
            enable_filtering)
        if '$ref' in parameter_obj:
            reference = parameter_obj['$ref'].replace(ref_path, '')
            type_ref = type_dict.get(reference, None)
            if type_ref is None:
                return None
            if 'properties' in type_ref:
                for property_name, property_value in six.iteritems(
                        type_ref['properties']):
                    prop = {'in': 'query', 'name': property_name}
                    prop['schema'] = {}
                    if 'type' in property_value:
                        prop['schema']['type'] = property_value['type']
                        if property_value['type'] == 'array':
                            prop['schema']['items'] = property_value['items']
                            if '$ref' in property_value['items']:
                                ref = property_value['items']['$ref'].replace(
                                    ref_path, '')
                                type_ref = type_dict[ref]
                                prop['schema']['items'] = type_ref
                                if 'description' in prop['schema']['items']:
                                    del prop['schema']['items']['description']
                        if 'description' in property_value:
                            prop['description'] = property_value['description']
                    elif '$ref' in property_value:
                        reference = property_value['$ref'].replace(
                            ref_path, '')
                        prop_obj = type_dict[reference]
                        prop['schema'] = prop_obj
                    if 'required' in type_ref:
                        if property_name in type_ref['required']:
                            prop['required'] = True
                        else:
                            prop['required'] = False
                    prop_array.append(prop)
            else:
                prop = {
                    'in': 'query',
                    'name': query_param_info['name'],
                    'description': type_ref['description'],
                    'schema': type_ref}
                prop_array.append(prop)
        else:
            parameter_obj['in'] = 'query'
            parameter_obj['name'] = query_param_info.name
            parameter_obj['description'] = query_param_info.documentation
            if 'required' not in parameter_obj:
                parameter_obj['required'] = True
            parameter_obj['schema'] = {"type": parameter_obj['type']}
            del parameter_obj['type']

            prop_array.append(parameter_obj)
        return prop_array
