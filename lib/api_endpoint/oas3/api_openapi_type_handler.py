import six
from lib import utils

def metamodel_to_swagger_type_converter(input_type):
    """
    Converts API Metamodel type to their equivalent Swagger type.
    A tuple is returned. first value of tuple is main type.
    second value of tuple has 'format' information, if available.
    """
    input_type = input_type.lower()
    if input_type == 'date_time':
        return 'string', 'date-time'
    if input_type == 'secret':
        return 'string', 'password'
    if input_type == 'any_error':
        return 'string', None
    if input_type == 'dynamic_structure':
        return 'object', None
    if input_type == 'uri':
        return 'string', 'uri'
    if input_type == 'id':
        return 'string', None
    if input_type == 'long':
        return 'integer', 'int64'
    if input_type == 'double':
        return 'number', 'double'
    if input_type == 'binary':
        return 'string', 'binary'
    return input_type, None

class typeHandler():

    def __init__(self):
        pass
        
    def visit_type_category(self, struct_type, new_prop, type_dict, structure_svc, enum_svc, ref_path, enable_filtering):
        if isinstance(struct_type, dict):
            return self.visit_type_category_dict(struct_type, new_prop, type_dict, structure_svc, enum_svc, ref_path, enable_filtering)
        if struct_type.category == 'BUILTIN':
            self.visit_builtin(struct_type.builtin_type, new_prop)
        elif struct_type.category == 'GENERIC':
            self.visit_generic(struct_type.generic_instantiation, new_prop, type_dict, structure_svc,
                        enum_svc, ref_path, enable_filtering)
        elif struct_type.category == 'USER_DEFINED':
            self.visit_user_defined(struct_type.user_defined_type, new_prop, type_dict, structure_svc,
                            enum_svc, ref_path, enable_filtering)


    def visit_type_category_dict(self, struct_type, new_prop, type_dict, structure_svc, enum_svc, ref_path, enable_filtering):
        new_prop['required'] = True
        if struct_type['category'] == 'BUILTIN':
            self.visit_builtin(struct_type['builtin_type'], new_prop)
        elif struct_type['category'] == 'GENERIC':
            self.visit_generic(struct_type['generic_instantiation'], new_prop, type_dict, structure_svc,
                        enum_svc, ref_path, enable_filtering)
        elif struct_type['category'] == 'USER_DEFINED':
            self.visit_user_defined(struct_type['user_defined_type'], new_prop, type_dict, structure_svc,
                            enum_svc, ref_path, enable_filtering)


    def visit_builtin(self, builtin_type, new_prop):
        data_type, format_ = metamodel_to_swagger_type_converter(builtin_type)
        if 'type' in new_prop and new_prop['type'] == 'array':
            item_obj = {'type': data_type}
            new_prop['items'] = item_obj
            if format_ is not None:
                item_obj['format'] = format_
        else:
            new_prop['type'] = data_type
            if format_ is not None:
                new_prop['format'] = format_


    def visit_generic(self, generic_instantiation, new_prop, type_dict, structure_svc, enum_svc, ref_path, enable_filtering):
        if generic_instantiation.generic_type == 'OPTIONAL':
            new_prop['required'] = False
            self.visit_type_category(generic_instantiation.element_type, new_prop, type_dict,
                                structure_svc, enum_svc, ref_path, enable_filtering)
        elif generic_instantiation.generic_type == 'LIST':
            new_prop['type'] = 'array'
            self.visit_type_category(generic_instantiation.element_type, new_prop, type_dict,
                                structure_svc, enum_svc, ref_path, enable_filtering)
        elif generic_instantiation.generic_type == 'SET':
            new_prop['type'] = 'array'
            new_prop['uniqueItems'] = True
            self.visit_type_category(generic_instantiation.element_type, new_prop, type_dict,
                                structure_svc, enum_svc, ref_path, enable_filtering)
        elif generic_instantiation.generic_type == 'MAP':
            # Have static key/value pair object maping for /rest paths
            # while use additionalProperties for /api paths
            new_type = {'type': 'object', 'additionalProperties': {}}

            if generic_instantiation.map_value_type.category == 'USER_DEFINED':
                new_type['additionalProperties'] = {
                        '$ref': ref_path + generic_instantiation.map_value_type.user_defined_type.resource_id
                    }
                res_type = generic_instantiation.map_value_type.user_defined_type.resource_type
                res_id = generic_instantiation.map_value_type.user_defined_type.resource_id
                self.check_type(res_type, res_id, type_dict, structure_svc, enum_svc, ref_path, enable_filtering)

            elif generic_instantiation.map_value_type.category == 'BUILTIN':
                new_type['additionalProperties'] = {'type': metamodel_to_swagger_type_converter(
                    generic_instantiation.map_value_type.builtin_type)[0]}
                
            elif generic_instantiation.map_value_type.category == 'GENERIC':
                temp_new_type = {}
                self.visit_generic( generic_instantiation.map_value_type.generic_instantiation,
                            temp_new_type, type_dict, structure_svc, enum_svc, ref_path, enable_filtering)             
                new_type['additionalProperties'] = temp_new_type
                
            new_prop.update(new_type)

            if 'additionalProperties' in new_type:
                if not new_type['additionalProperties'].get('required', True):
                    del new_type['additionalProperties']['required']

            if '$ref' in new_prop:
                del new_prop['$ref']


    def is_type_builtin(self, type_):
        type_ = type_.lower()
        typeset = {'binary', 'boolean', 'datetime', 'double', 'dynamicstructure', 'exception',
                'id', 'long', 'opaque', 'secret', 'string', 'uri'}
        if type_ in typeset:
            return True
        return False

    def get_structure_info(self, struct_type, structure_svc, enable_filtering):
        """
        Given a type, return its structure info, if the type is a structure.
        """
        try:
            structure_info = structure_svc.get(struct_type)
            if structure_info is None:
                utils.eprint("Could not fetch structure info for " + struct_type)
            elif utils.is_filtered(structure_info.metadata, enable_filtering):
                return None
            else:
                structure_info.fields = [field for field in structure_info.fields if not utils.is_filtered(field.metadata, enable_filtering)]
                return structure_info
        except Exception as ex:
            eprint("Error fetching structure info for " + struct_type)
            eprint(ex)
            return None


    def process_structure_info(self, type_name, structure_info, type_dict, structure_svc, enum_svc, ref_path, enable_filtering):
        new_type = {'type': 'object', 'properties': {}}
        for field in structure_info.fields:
            newprop = {'description': field.documentation}
            if field.type.category == 'BUILTIN':
                self.visit_builtin(field.type.builtin_type, newprop)
            elif field.type.category == 'GENERIC':
                self.visit_generic(field.type.generic_instantiation, newprop, type_dict,
                            structure_svc, enum_svc, ref_path, enable_filtering)
            elif field.type.category == 'USER_DEFINED':
                self.visit_user_defined(field.type.user_defined_type, newprop, type_dict,
                                structure_svc, enum_svc, ref_path, enable_filtering)
            new_type['properties'].setdefault(field.name, newprop)
        required = []
        for property_name, property_value in six.iteritems(new_type['properties']):
            if 'required' not in property_value:
                required.append(property_name)
            elif property_value['required'] == 'true':
                required.append(property_name)
        if len(required) > 0:
            new_type['required'] = required
        type_dict[type_name] = new_type

    def get_enum_info(self, type_name, enum_svc, enable_filtering):
        """
        Given a type, return its enum info, if the type is enum.
        """
        try:
            enum_info = enum_svc.get(type_name)
            if enum_info is None:
                utils.eprint("Could not fetch enum info for " + type_name)
            elif utils.is_filtered(enum_info.metadata, enable_filtering):
                return None
            else:
                return enum_info
        except Exception as exception:
            utils.eprint("Error fetching enum info for " + type_name)
            utils.eprint(exception)
            return None

    def process_enum_info(self, type_name, enum_info, type_dict, enable_filtering):
        enum_type = {'type': 'string', 'description': enum_info.documentation}
        enum_type.setdefault('enum', [value.value for value in enum_info.values if not utils.is_filtered(value.metadata, enable_filtering)])
        type_dict[type_name] = enum_type

    def check_type(self, resource_type, type_name, type_dict, structure_svc, enum_svc, ref_path, enable_filtering):
        if type_name in type_dict or self.is_type_builtin(type_name):
            return
        if resource_type == 'com.vmware.vapi.structure':
            structure_info = self.get_structure_info(type_name, structure_svc, enable_filtering)
            if structure_info is not None:
                # Mark it as visited to handle recursive definitions. (Type A referring to Type A in one of the fields).
                type_dict[type_name] = {}
                self.process_structure_info(type_name, structure_info, type_dict, structure_svc, enum_svc, ref_path, enable_filtering)
        else:
            enum_info = self.get_enum_info(type_name, enum_svc, enable_filtering)
            if enum_info is not None:
                # Mark it as visited to handle recursive definitions. (Type A referring to Type A in one of the fields).
                type_dict[type_name] = {}
                self.process_enum_info(type_name, enum_info, type_dict, enable_filtering)

    def visit_user_defined(self, user_defined_type, newprop, type_dict, structure_svc, enum_svc, ref_path, enable_filtering):
        if user_defined_type.resource_id is None:
            return
        if 'type' in newprop and newprop['type'] == 'array':
            item_obj = {'$ref': ref_path + user_defined_type.resource_id}
            newprop['items'] = item_obj
        # if not array, fill in type or ref
        else:
            newprop['$ref'] = ref_path + user_defined_type.resource_id

        self.check_type(user_defined_type.resource_type, user_defined_type.resource_id, type_dict, structure_svc, enum_svc, ref_path, enable_filtering)