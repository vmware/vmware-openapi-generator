import six
from lib import utils


class TypeHandlerCommon():

    def __init__(self, show_unreleased_apis):
        self.show_unreleased_apis = show_unreleased_apis

    def visit_type_category(
            self,
            struct_type,
            new_prop,
            type_dict,
            structure_svc,
            enum_svc,
            ref_path):
        if isinstance(struct_type, dict):
            return self.visit_type_category_dict(
                struct_type,
                new_prop,
                type_dict,
                structure_svc,
                enum_svc,
                ref_path)
        if struct_type.category == 'BUILTIN':
            self.visit_builtin(struct_type.builtin_type, new_prop)
        elif struct_type.category == 'GENERIC':
            self.visit_generic(
                struct_type.generic_instantiation,
                new_prop,
                type_dict,
                structure_svc,
                enum_svc,
                ref_path)
        elif struct_type.category == 'USER_DEFINED':
            self.visit_user_defined(
                struct_type.user_defined_type,
                new_prop,
                type_dict,
                structure_svc,
                enum_svc,
                ref_path)

    def visit_type_category_dict(
            self,
            struct_type,
            new_prop,
            type_dict,
            structure_svc,
            enum_svc,
            ref_path):
        new_prop['required'] = True
        if struct_type['category'] == 'BUILTIN':
            self.visit_builtin(struct_type['builtin_type'], new_prop)
        elif struct_type['category'] == 'GENERIC':
            self.visit_generic(
                struct_type['generic_instantiation'],
                new_prop,
                type_dict,
                structure_svc,
                enum_svc,
                ref_path)
        elif struct_type['category'] == 'USER_DEFINED':
            self.visit_user_defined(
                struct_type['user_defined_type'],
                new_prop,
                type_dict,
                structure_svc,
                enum_svc,
                ref_path)

    def visit_builtin(self, builtin_type, new_prop):
        data_type, format_ = utils.metamodel_to_swagger_type_converter(
            builtin_type)
        if 'type' in new_prop and new_prop['type'] == 'array':
            item_obj = {'type': data_type}
            new_prop['items'] = item_obj
            if format_ is not None:
                item_obj['format'] = format_
        else:
            new_prop['type'] = data_type
            if format_ is not None:
                new_prop['format'] = format_

    def visit_generic(
            self,
            generic_instantiation,
            new_prop,
            type_dict,
            structure_svc,
            enum_svc,
            ref_path):
        pass

    def get_structure_info(self, struct_type, structure_svc):
        if self.show_unreleased_apis:
            return self.__get_structure_info(struct_type, structure_svc)
        else:
            return self.__get_structure_info_filtered(struct_type, structure_svc)

    def __get_structure_info(self, struct_type, structure_svc):
        try:
            structure_info = structure_svc.get(struct_type)
            if structure_info is None:
                utils.eprint(
                    "Could not fetch structure info for " +
                    struct_type)
            return structure_info
        except Exception as ex:
            utils.eprint("Error fetching structure info for " + struct_type)
            utils.eprint(ex)
            return None

    def __get_structure_info_filtered(self, struct_type, structure_svc):
        structure_info = self.__get_structure_info(struct_type, structure_svc)
        if structure_info is None or utils.is_filtered(structure_info.metadata):
            return None
        structure_info.fields = [field for field in structure_info.fields if not utils.is_filtered(field.metadata)]
        return structure_info

    def process_structure_info(
            self,
            type_name,
            structure_info,
            type_dict,
            structure_svc,
            enum_svc,
            ref_path):
        new_type = {'type': 'object', 'properties': {}}
        for field in structure_info.fields:
            newprop = {'description': field.documentation}
            if field.type.category == 'BUILTIN':
                self.visit_builtin(field.type.builtin_type, newprop)
            elif field.type.category == 'GENERIC':
                self.visit_generic(
                    field.type.generic_instantiation,
                    newprop,
                    type_dict,
                    structure_svc,
                    enum_svc,
                    ref_path)
            elif field.type.category == 'USER_DEFINED':
                self.visit_user_defined(
                    field.type.user_defined_type,
                    newprop,
                    type_dict,
                    structure_svc,
                    enum_svc,
                    ref_path)
            #new_type['properties'].setdefault(field.name, newprop)
            new_type['properties'].setdefault(self.get_fieldname(field), newprop)
        required = []
        for property_name, property_value in six.iteritems(
                new_type['properties']):
            if 'required' not in property_value:
                required.append(property_name)
            elif property_value['required'] == 'true':
                required.append(property_name)
        if len(required) > 0:
            new_type['required'] = required
        type_dict[type_name] = new_type

    def get_fieldname(self, field):
        if hasattr(field, "metadata") and "SerializationName" in field.metadata:
            return field.metadata["SerializationName"].elements["value"].string_value
        else:
            return field.name

    def get_enum_info(self, type_name, enum_svc):
        if self.show_unreleased_apis:
            return self.__get_enum_info(type_name, enum_svc)
        else:
            return self.__get_enum_info_filtered(type_name, enum_svc)

    def __get_enum_info(self, type_name, enum_svc):
        try:
            enum_info = enum_svc.get(type_name)
            if enum_info is None:
                utils.eprint("Could not fetch enum info for " + type_name)
            return enum_info
        except Exception as exception:
            utils.eprint("Error fetching enum info for " + type_name)
            utils.eprint(exception)
            return None

    def __get_enum_info_filtered(self, type_name, enum_svc):
        enum_info = self.__get_enum_info(type_name, enum_svc)
        if enum_info is None or utils.is_filtered(enum_info.metadata):
            return None
        return enum_info

    def process_enum_info(
            self,
            type_name,
            enum_info,
            type_dict):
        enum_type = {'type': 'string', 'description': enum_info.documentation}
        if self.show_unreleased_apis:
            enum_type.setdefault('enum',  [value.value for value in enum_info.values])
        else:
            enum_type.setdefault(
                'enum', [value.value for value in enum_info.values if not utils.is_filtered(value.metadata)])
        type_dict[type_name] = enum_type

    def check_type(
            self,
            resource_type,
            type_name,
            type_dict,
            structure_svc,
            enum_svc,
            ref_path):
        if type_name in type_dict or utils.is_type_builtin(type_name):
            return
        if resource_type == 'com.vmware.vapi.structure':
            structure_info = self.get_structure_info(type_name, structure_svc)
            if structure_info is not None:
                # Mark it as visited to handle recursive definitions. (Type A
                # referring to Type A in one of the fields).
                type_dict[type_name] = {}
                self.process_structure_info(
                    type_name,
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
                type_dict[type_name] = {}
                self.process_enum_info(
                    type_name, enum_info, type_dict)

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
        if 'type' in newprop and newprop['type'] == 'array':
            item_obj = {'$ref': ref_path + user_defined_type.resource_id}
            newprop['items'] = item_obj
        # if not array, fill in type or ref
        else:
            newprop['$ref'] = ref_path + user_defined_type.resource_id

        self.check_type(
            user_defined_type.resource_type,
            user_defined_type.resource_id,
            type_dict,
            structure_svc,
            enum_svc,
            ref_path)
