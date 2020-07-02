# Copyright 2020 VMware, Inc.
# SPDX-License-Identifier: MIT

from lib import utils
from lib.type_handler_common import TypeHandlerCommon


class ApiTypeHandler(TypeHandlerCommon):

    def __init__(self, show_unreleased_apis):
        TypeHandlerCommon.__init__(self, show_unreleased_apis)

    def visit_generic(
            self,
            generic_instantiation,
            new_prop,
            type_dict,
            structure_svc,
            enum_svc,
            ref_path):
        if generic_instantiation.generic_type == 'OPTIONAL':
            new_prop['required'] = False
            self.visit_type_category(
                generic_instantiation.element_type,
                new_prop,
                type_dict,
                structure_svc,
                enum_svc,
                ref_path)
        elif generic_instantiation.generic_type == 'LIST':
            new_prop['type'] = 'array'
            self.visit_type_category(
                generic_instantiation.element_type,
                new_prop,
                type_dict,
                structure_svc,
                enum_svc,
                ref_path)
        elif generic_instantiation.generic_type == 'SET':
            new_prop['type'] = 'array'
            new_prop['uniqueItems'] = True
            self.visit_type_category(
                generic_instantiation.element_type,
                new_prop,
                type_dict,
                structure_svc,
                enum_svc,
                ref_path)
        elif generic_instantiation.generic_type == 'MAP':
            # Have static key/value pair object maping for /rest paths
            # while use additionalProperties for /api paths
            new_type = {'type': 'object', 'additionalProperties': {}}

            if generic_instantiation.map_value_type.category == 'USER_DEFINED':
                new_type['additionalProperties'] = {
                    '$ref': ref_path + utils.get_str_camel_case(
                        generic_instantiation.map_value_type.user_defined_type.resource_id,
                        *utils.CAMELCASE_SEPARATOR_LIST)}
                res_type = generic_instantiation.map_value_type.user_defined_type.resource_type
                res_id = generic_instantiation.map_value_type.user_defined_type.resource_id
                self.check_type(
                    res_type,
                    res_id,
                    type_dict,
                    structure_svc,
                    enum_svc,
                    ref_path)

            elif generic_instantiation.map_value_type.category == 'BUILTIN':
                new_type['additionalProperties'] = {
                    'type': utils.metamodel_to_swagger_type_converter(
                        generic_instantiation.map_value_type.builtin_type)[0]}

            elif generic_instantiation.map_value_type.category == 'GENERIC':
                temp_new_type = {}
                self.visit_generic(
                    generic_instantiation.map_value_type.generic_instantiation,
                    temp_new_type,
                    type_dict,
                    structure_svc,
                    enum_svc,
                    ref_path)
                new_type['additionalProperties'] = temp_new_type

            new_prop.update(new_type)

            if 'additionalProperties' in new_type:
                if not new_type['additionalProperties'].get('required', True):
                    del new_type['additionalProperties']['required']

            if '$ref' in new_prop:
                del new_prop['$ref']

    def check_type(
            self,
            resource_type,
            type_name,
            type_dict,
            structure_svc,
            enum_svc,
            ref_path):
        camel_cased_type_name = utils.get_str_camel_case(type_name, *utils.CAMELCASE_SEPARATOR_LIST)
        if camel_cased_type_name in type_dict or utils.is_type_builtin(type_name):
            return
        if resource_type == 'com.vmware.vapi.structure':
            structure_info = self.get_structure_info(type_name, structure_svc)
            if structure_info is not None:
                # Mark it as visited to handle recursive definitions. (Type A
                # referring to Type A in one of the fields).
                type_dict[camel_cased_type_name] = {}
                self.process_structure_info(
                    camel_cased_type_name,
                    structure_info,
                    type_dict,
                    structure_svc,
                    enum_svc,
                    ref_path)
        else:
            enum_info = self.get_enum_info(type_name, enum_svc)
            if enum_info is not None:
                # Mark it as visited to handle recursive definitions. (Type A
                # referring to Type A in one of the fields).
                type_dict[camel_cased_type_name] = {}
                self.process_enum_info(
                    camel_cased_type_name, enum_info, type_dict)

    def visit_user_defined(
            self,
            user_defined_type,
            newprop,
            type_dict,
            structure_svc,
            enum_svc,
            ref_path):
        if user_defined_type.resource_id is None:
            return
        camel_cased_ref = utils.get_str_camel_case(user_defined_type.resource_id,
                                                   *utils.CAMELCASE_SEPARATOR_LIST)
        if 'type' in newprop and newprop['type'] == 'array':
            item_obj = {'$ref': ref_path + camel_cased_ref}
            newprop['items'] = item_obj
        # if not array, fill in type or ref
        else:
            newprop['$ref'] = ref_path + camel_cased_ref

        self.check_type(
            user_defined_type.resource_type,
            user_defined_type.resource_id,
            type_dict,
            structure_svc,
            enum_svc,
            ref_path)