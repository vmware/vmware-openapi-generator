# Copyright 2020 VMware, Inc.
# SPDX-License-Identifier: MIT

import six
from lib import utils
from lib.api_endpoint.api_type_handler import ApiTypeHandler


class ApiSwaggerParaHandler():

    def convert_field_info_to_swagger_parameter(
            self,
            param_type,
            input_parameter_obj,
            type_dict,
            structure_svc,
            enum_svc,
            show_unreleased_apis):
        """
        Converts metamodel fieldinfo to swagger parameter.
        """
        parameter_obj = {}
        ref_path = "#/definitions/"
        tpHandler = ApiTypeHandler(show_unreleased_apis)
        tpHandler.visit_type_category(
            input_parameter_obj.type,
            parameter_obj,
            type_dict,
            structure_svc,
            enum_svc,
            ref_path)
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
        return parameter_obj

    def wrap_body_params(
            self,
            service_name,
            operation_name,
            content_type,
            body_param_list,
            type_dict,
            structure_svc,
            enum_svc,
            show_unreleased_apis):
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
        wrapper_name = utils.get_str_camel_case(service_name + '_' + operation_name,  *utils.CAMELCASE_SEPARATOR_LIST)
        body_obj = {}
        properties_obj = {}
        required = []
        ref_path = "#/definitions/"
        tpHandler = ApiTypeHandler(show_unreleased_apis)
        for param in body_param_list:
            parameter_obj = {}
            tpHandler.visit_type_category(
                param.type,
                parameter_obj,
                type_dict,
                structure_svc,
                enum_svc,
                ref_path)
            parameter_obj['description'] = param.documentation
            if 'BodyField' in param.metadata:
                body_obj['type'] = 'object'
                body_obj['properties'] = properties_obj
                properties_obj[param.metadata['BodyField'].elements['name'].string_value] = parameter_obj
                if 'required' not in parameter_obj:
                    required.append(param.name)
                elif parameter_obj['required'] == 'true':
                    required.append(param.name)
            else:
                body_obj.update(parameter_obj)

        parameter_obj = {'in': 'body', 'name': 'request_body'}
        if len(required) > 0:
            body_obj['required'] = required
            parameter_obj['required'] = True
        elif 'required' in body_obj:
            del body_obj['required']

        type_dict[wrapper_name] = body_obj

        if content_type == 'FORM_URLENCODED':
            return self.wrap_form_data_params(type_dict, wrapper_name)

        schema_obj = {'$ref': ref_path + wrapper_name}
        parameter_obj['schema'] = schema_obj
        return parameter_obj

    def wrap_form_data_params(self, type_dict, wrapper_name):
        parameter_list = []
        definition = type_dict[wrapper_name]
        if "properties" in definition:
            for property_name, property_value in definition["properties"].items():
                formDataEntry = {"in": "formData",
                                 "name": property_name}
                formDataEntry.update({k: v for k, v in property_value.items() if k in ['type', 'description']})
                if "required" in definition and property_name in definition["required"]:
                    formDataEntry["required"] = "true";
                parameter_list.append(formDataEntry)
        elif "$ref" in definition:
            reference = definition["$ref"].replace("#/definitions/", "")
            return self.wrap_form_data_params(type_dict, reference)
        return parameter_list

    def flatten_query_param_spec(
            self,
            query_param_info,
            type_dict,
            structure_svc,
            enum_svc,
            show_unreleased_apis):
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
        ref_path = "#/definitions/"
        tpHandler = ApiTypeHandler(show_unreleased_apis)
        tpHandler.visit_type_category(
            query_param_info.type,
            parameter_obj,
            type_dict,
            structure_svc,
            enum_svc,
            ref_path)
        if '$ref' in parameter_obj:
            reference = parameter_obj['$ref'].replace(ref_path, '')
            type_ref = type_dict.get(reference, None)
            if type_ref is None:
                return None
            if 'properties' in type_ref:
                for property_name, property_value in six.iteritems(
                        type_ref['properties']):
                    prop = {'in': 'query', 'name': property_name}
                    if 'type' in property_value:
                        prop['type'] = property_value['type']
                        if prop['type'] == 'array':
                            prop['collectionFormat'] = 'multi'
                            prop['items'] = property_value['items']
                            if '$ref' in property_value['items']:
                                ref = property_value['items']['$ref'].replace(
                                    ref_path, '')
                                type_ref = type_dict[ref]
                                prop['items'] = type_ref
                                if 'description' in prop['items']:
                                    del prop['items']['description']
                        if 'description' in property_value:
                            prop['description'] = property_value['description']
                    elif '$ref' in property_value:
                        reference = property_value['$ref'].replace(
                            ref_path, '')
                        prop_obj = type_dict[reference]
                        if 'type' in prop_obj:
                            prop['type'] = prop_obj['type']
                            # Query parameter's type is object, Coverting it to
                            # string given type object for query is not
                            # supported by swagger 2.0.
                            if prop['type'] == "object":
                                prop['type'] = "string"
                        if 'enum' in prop_obj:
                            prop['enum'] = prop_obj['enum']
                        if 'description' in prop_obj:
                            prop['description'] = prop_obj['description']
                    if 'required' in type_ref:
                        if property_name in type_ref['required']:
                            prop['required'] = True
                        else:
                            prop['required'] = False
                    prop_array.append(prop)
            else:
                prop = {
                    'in': 'query',
                    'name': query_param_info.name,
                    'description': type_ref['description'],
                    'type': type_ref['type']}
                if 'enum' in type_ref:
                    prop['enum'] = type_ref['enum']
                if 'required' not in parameter_obj:
                    prop['required'] = True
                else:
                    prop['required'] = parameter_obj['required']
                prop_array.append(prop)
        else:
            parameter_obj['in'] = 'query'
            parameter_obj['name'] = query_param_info.name
            parameter_obj['description'] = query_param_info.documentation
            if 'required' not in parameter_obj:
                parameter_obj['required'] = True
            prop_array.append(parameter_obj)
        return prop_array
