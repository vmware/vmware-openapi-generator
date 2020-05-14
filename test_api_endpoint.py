import unittest
from unittest import mock 
from lib.api_endpoint.api_type_handler import ApiTypeHandler
from lib.api_endpoint.api_url_processing import ApiUrlProcessing
from lib.api_endpoint.api_metamodel2spec import ApiMetamodel2Spec
from lib.api_endpoint.swagger2.api_swagger_parameter_handler import ApiSwaggerParaHandler
from lib.api_endpoint.oas3.api_openapi_parameter_handler import ApiOpenapiParaHandler

class TestApiTypeHandler(unittest.TestCase):

    api_tphandler = ApiTypeHandler()

    def test_visit_generic(self):
        # case 1: when generic instantiation type is 'SET' and category is 'BUILT-IN'
        generic_instantiation_element_type_mock = mock.Mock() 
        generic_instantiation_element_type_mock.category = 'BUILTIN'
        generic_instantiation_element_type_mock.builtin_type = 'date-time'
        generic_instantiation_mock = mock.Mock()
        generic_instantiation_mock.generic_type = 'SET'
        generic_instantiation_mock.element_type = generic_instantiation_element_type_mock
        
        field_info_mock = mock.Mock()
        field_info_type = mock.Mock()
        field_info_type.category = 'BUILTIN'
        field_info_type.builtin_type = 'date-time'
        field_info_mock.type = field_info_type
        field_info_mock.generic_instantiation = generic_instantiation_mock
        field_info_mock.documentation = 'fieldInfoMockDescription'
        field_info_mock.name = 'fieldInfoMockName'
        structure_info_mock = mock.Mock()
        structure_info_mock.fields = [field_info_mock]
        structure_dict = {
            'com.vmware.package.mock': structure_info_mock
        }
        '''
        The structure dict looks like: 
        structure_dict = {
            'com.vmware.package.mock': StructureInfo( fields = [ FieldInfo(
                name = 'fieldInfoMockName', documentation =  'fieldInfoMockDescription',
                generic_instantiation = GenericInstantiation( generic_type = 'SET',
                element_type = Type( category = 'BUILTIN', builtin_type = 'date-time'))
            )])
        }
        '''
        new_prop = {}
        self.api_tphandler.visit_generic(generic_instantiation_mock, new_prop, {}, structure_dict, {}, '#/definitions/', False )
        new_prop_expected = {'type': 'array', 'uniqueItems': True, 'items': {'type': 'date-time'}}
        self.assertEqual(new_prop_expected, new_prop)

        # case 2: when generic instantiation type is 'OPTIONAL' and category is 'BUILT-IN'
        generic_instantiation_mock.generic_type = 'OPTIONAL'
        new_prop = {}
        self.api_tphandler.visit_generic(generic_instantiation_mock, new_prop, {}, structure_dict, {}, '#/definitions/', False )
        new_prop_expected = {'required': False, 'type': 'date-time'}
        self.assertEqual(new_prop_expected, new_prop)

        # case 3: when generic instantiation type is 'LIST' and category is 'USER-DEFINED'
        generic_instantiation_mock.generic_type = 'LIST'
        user_defined_type_mock = mock.Mock()
        user_defined_type_mock.resource_type = 'com.vmware.vapi.structure'
        user_defined_type_mock.resource_id = 'com.vmware.package.mock'
        generic_instantiation_element_type_mock.category = 'USER_DEFINED'
        generic_instantiation_element_type_mock.user_defined_type = user_defined_type_mock
        '''
        The structure dict looks like: 
        structure_dict = {
            'com.vmware.package.mock': StructureInfo( fields = [ FieldInfo(
                name = 'fieldInfoMockName', documentation =  'fieldInfoMockDescription',
                generic_instantiation = GenericInstantiation( generic_type = 'LIST',
                element_type = Type( category = 'USER_DEFINED', user_defined_type = UserDefinedType(
                    resource_type = 'com.vmware.vapi.structure', resource_id = 'com.vmware.package.mock'
                )))
            )])
        }
        '''
        new_prop = {}
        self.api_tphandler.visit_generic(generic_instantiation_mock, new_prop, {}, structure_dict, {}, '#/definitions/', False )
        new_prop_expected = {'type': 'array', 'items': {'$ref': '#/definitions/com.vmware.package.mock'}}
        self.assertEqual(new_prop_expected, new_prop)

        # case 4: when generic instantiation type is 'MAP'
        # case 4.1 : map key and value type is 'BUILTIN'
        map_key_type_mock = mock.Mock()
        map_key_type_mock.category = 'BUILTIN'
        map_key_type_mock.builtin_type = 'long'
        map_value_type_mock = mock.Mock()
        map_value_type_mock.category = 'BUILTIN'
        map_value_type_mock.builtin_type = 'long'
        generic_instantiation_mock = mock.Mock()
        generic_instantiation_mock.generic_type = 'MAP'
        generic_instantiation_mock.map_key_type = map_key_type_mock
        generic_instantiation_mock.map_value_type = map_value_type_mock
        '''
        The structure dict looks like: 
        structure_dict = {
            'com.vmware.package.mock': StructureInfo( fields = [ FieldInfo(
                name = 'fieldInfoMockName', documentation =  'fieldInfoMockDescription',
                generic_instantiation = GenericInstantiation( generic_type = 'MAP',
                map_key_type = MapKeyType( category = 'BUILTIN', builtin_type = 'long'),
                map_value_type = MapValueType( category = 'BUILTIN', builtin_type = 'long')
                )
            )])
        }
        '''
        new_prop = {}
        self.api_tphandler.visit_generic(generic_instantiation_mock, new_prop, {}, structure_dict, {}, '#/definitions/', False )
        new_prop_expected = {'type': 'object', 'additionalProperties': {'type': 'integer'}}
        self.assertEqual(new_prop_expected, new_prop)

        # case 4.2: map key and value type is 'USER_DEFINED'
        map_value_type_mock.category = 'USER_DEFINED'
        map_value_type_mock.user_defined_type = user_defined_type_mock
        type_dict = {
        'com.vmware.package.mock': {}
        }
        new_prop = {}
        self.api_tphandler.visit_generic(generic_instantiation_mock, new_prop, type_dict, structure_dict, {}, '#/definitions/', False )
        new_prop_expected = {'type': 'object', 'additionalProperties': {'$ref': '#/definitions/com.vmware.package.mock'}}
        self.assertEqual(new_prop_expected, new_prop)

        # case 4.3: map key and value type is 'GENERIC'
        generic_instantiation_map_value_type_mock = mock.Mock()
        generic_instantiation_map_value_type_mock.generic_type = 'OPTIONAL'
        generic_instantiation_map_value_type_mock.element_type = generic_instantiation_element_type_mock
        map_value_type_mock.category = 'GENERIC'
        map_value_type_mock.generic_instantiation = generic_instantiation_map_value_type_mock
        new_prop = {}
        self.api_tphandler.visit_generic(generic_instantiation_mock, new_prop, type_dict, structure_dict, {}, '#/definitions/', False )
        new_prop_expected = {'type': 'object', 'additionalProperties': {'$ref': '#/definitions/com.vmware.package.mock'}}
        self.assertEqual(new_prop_expected, new_prop)

class TestApiUrlProcessing(unittest.TestCase):

    def test_api_get_url_and_method(self):
        # http operation inside metadata belongs to put, post, patch, get or delete
        element_info_mock =  mock.Mock()
        element_value_mock = mock.Mock()
        element_value_mock.string_value = 'some-url-path'
        element_info_mock.elements = { 'path': element_value_mock}
        metadata = {'POST': element_info_mock}
        method_expected = 'POST'
        url_path_expected = 'some-url-path'
        api_url_process = ApiUrlProcessing()
        method_actual, url_path_actual = api_url_process.api_get_url_and_method(metadata)
        self.assertEqual(method_expected, method_actual)
        self.assertEqual(url_path_expected, url_path_actual)

class TestApiMetamodel2Spec(unittest.TestCase):

    element_value_mock = mock.Mock()
    element_value_mock.string_value = 'mock'
    element_map_mock = mock.Mock()
    element_map_mock.elements = {'value': element_value_mock}
    user_defined_type_mock = mock.Mock()
    user_defined_type_mock.resource_type = 'com.vmware.vapi.structure'
    user_defined_type_mock.resource_id = 'com.vmware.package.mock'
    field_info_type = mock.Mock()
    field_info_type.category = 'USER_DEFINED'
    field_info_type.user_defined_type = user_defined_type_mock
    field_info_mock_1 = mock.Mock()
    field_info_mock_1.name = 'mock_name_1'
    field_info_mock_1.metadata = {'PathVariable' :  element_map_mock}
    field_info_mock_1.documentation = 'mock documentation for field info 1'
    field_info_mock_1.type = field_info_type
    field_info_mock_2 = mock.Mock()
    field_info_mock_2.name = 'mock_name_2'
    field_info_mock_2.metadata = {'Body' :  element_map_mock}
    field_info_mock_2.documentation = 'mock documentation for field info 2'
    field_info_mock_2.type = field_info_type
    field_info_mock_3 = mock.Mock()
    field_info_mock_3.name = 'mock_name_3'
    field_info_mock_3.metadata = {'Query' :  element_map_mock}
    field_info_mock_3.documentation = 'mock documentation for field info 3'
    field_info_mock_3.type = field_info_type
    field_info_mock_4 = mock.Mock()
    field_info_mock_4.name = 'mock_name_4'
    field_info_mock_4.metadata = {'metadata_key' :  element_map_mock}
    field_info_mock_4.documentation = 'mock documentation for field info 4'
    field_info_mock_4.type = field_info_type

    url = '/package/mock-1/{mock}'
    type_dict = {
        'com.vmware.package.mock' : { 
            'description' : 'mock description',
            'type': 'string',
            'enum' :['enum-1', 'enum-2']
        }
    }
    new_url_expected = '/package/mock-1/{mock_name_1}'
    api_meta2spec = ApiMetamodel2Spec()

    def test_process_put_post_patch_request(self):
        # case 1: create parameter array using field information of parameters for
        # put, post, patch operations in swagger 2.0
        params = [self.field_info_mock_1, self.field_info_mock_2, self.field_info_mock_3, self.field_info_mock_4]
        '''
        Below is the structure of the params list
        params = [
            FieldInfo(name = 'mock_name_1', documentation = 'mock documentation for field info 1',
            type = Type(category = 'USER_DEFINED', 
            user_defined_type = UserDefinedType( resource_type = 'com.vmware.vapi.structure', resource_id = 'com.vmware.package.mock')
                ), metadata = {
                    'PathVariable' : ElementMap( elements = {
                        'value': ElementValue(string_value = 'mock')
                    })
            ),
            FieldInfo(name = 'mock_name_2', documentation = 'mock documentation for field info 2',
            type = Type(category = 'USER_DEFINED', 
            user_defined_type = UserDefinedType( resource_type = 'com.vmware.vapi.structure', resource_id = 'com.vmware.package.mock')
                ), metadata = {
                    'Body' : ElementMap( elements = {
                        'value': ElementValue(string_value = 'mock')
                    })
            ),
            FieldInfo(name = 'mock_name_3', documentation = 'mock documentation for field info 3',
            type = Type(category = 'USER_DEFINED', 
            user_defined_type = UserDefinedType( resource_type = 'com.vmware.vapi.structure', resource_id = 'com.vmware.package.mock')
                ), metadata = {
                    'Query' : ElementMap( elements = {
                        'value': ElementValue(string_value = 'mock')
                    })
            ),
            FieldInfo(name = 'mock_name_4', documentation = 'mock documentation for field info 4',
            type = Type(category = 'USER_DEFINED', 
            user_defined_type = UserDefinedType( resource_type = 'com.vmware.vapi.structure', resource_id = 'com.vmware.package.mock')
                ), metadata = {
                    'metadata_key' : ElementMap( elements = {
                        'value': ElementValue(string_value = 'mock')
                    })
            )
        ]
        '''
        spec = ApiSwaggerParaHandler()
        par_array_actual, new_url_actual = self.api_meta2spec.process_put_post_patch_request(self.url, 'com.vmware.package.mock', 
                                                                                        'mock_operation_name', params, 
                                                                                        self.type_dict, {}, {}, False, spec)
        par_array_expected = [{
            'required': True,
            'in': 'path',
            'name': 'mock_name_1',
            'description': '{ 1. mock description }, { 2. mock documentation for field info 1 }',
            'type': 'string',
            'enum' :['enum-1', 'enum-2']
        }, {
            'in': 'body',
            'name': 'request_body',
            'schema': {
                '$ref': '#/definitions/com.vmware.package.mock_mock_operation_name'
            }
        },{
            'required': True,
            'in': 'query',
            'name': 'mock_name_3',
            'description': '{ 1. mock description }, { 2. mock documentation for field info 3 }',
            'type': 'string',
            'enum': ['enum-1', 'enum-2']
        },{
            'in': 'query',
            'name': 'mock_name_4',
            'description': 'mock description',
            'type': 'string',
            'enum': ['enum-1', 'enum-2'],
            'required': True
        }]
        self.assertEqual(par_array_expected, par_array_actual)
        self.assertEqual(self.new_url_expected, new_url_actual)

        # case 2: create parameter array using field information of parameters for
        # put, post, patch operations in openAPI 3.0
        spec  = ApiOpenapiParaHandler()
        par_array_actual, new_url_actual = self.api_meta2spec.process_put_post_patch_request(self.url, 'com.vmware.package.mock', 
                                                                                        'mock_operation_name', params, 
                                                                                        self.type_dict, {}, {}, False, spec)
        par_array_expected = [{
            'required': True,
            'in': 'path',
            'name': 'mock_name_1',
            'description': '{ 1. mock description }, { 2. mock documentation for field info 1 }',
            'enum' :['enum-1', 'enum-2'],
            'schema': {
                'type': 'string'
            }
        },
        {'$ref': '#/components/requestBodies/com.vmware.package.mock_mock_operation_name'},
        {
            'required': True,
            'in': 'query',
            'name': 'mock_name_3',
            'description': '{ 1. mock description }, { 2. mock documentation for field info 3 }',
            'enum': ['enum-1', 'enum-2'],
            'schema': {
                'type': 'string'
            }
        },{
            'in': 'query',
            'name': 'mock_name_4',
            'description': 'mock description',
            'schema':{
                'description': 'mock description',
                'type': 'string',
                'enum': ['enum-1', 'enum-2'],
            }
        }]
        self.assertEqual(par_array_expected, par_array_actual)
        self.assertEqual(self.new_url_expected, new_url_actual)


    def test_process_get_request(self):
        # case 1: create parameter array using field information of parameters for 
        # get operation in swagger 2.0
        params = [self.field_info_mock_1, self.field_info_mock_3, self.field_info_mock_4]
        spec = ApiSwaggerParaHandler()
        par_array_actual, new_url_actual = self.api_meta2spec.process_get_request( self.url, params, self.type_dict, {}, {}, False, spec)
        par_array_expected = [{
            'required': True,
            'in': 'path',
            'name': 'mock_name_1',
            'description': '{ 1. mock description }, { 2. mock documentation for field info 1 }',
            'type': 'string',
            'enum' :['enum-1', 'enum-2']
        }, {
            'required': True,
            'in': 'query',
            'name': 'mock_name_3',
            'description': '{ 1. mock description }, { 2. mock documentation for field info 3 }',
            'type': 'string',
            'enum': ['enum-1', 'enum-2']
        },{
            'in': 'query',
            'name': 'mock_name_4',
            'description': 'mock description',
            'type': 'string',
            'enum': ['enum-1', 'enum-2'],
            'required': True
        }]
        self.assertEqual(par_array_expected, par_array_actual)
        self.assertEqual(self.new_url_expected, new_url_actual)

        # case 2: create parameter array using field information of parameters for 
        # get operation in openAPI 3.0
        spec = ApiOpenapiParaHandler()
        par_array_actual, new_url_actual = self.api_meta2spec.process_get_request( self.url, params, self.type_dict, {}, {}, False, spec)
        par_array_expected = [{
            'required': True,
            'in': 'path',
            'name': 'mock_name_1',
            'description': '{ 1. mock description }, { 2. mock documentation for field info 1 }',
            'enum' :['enum-1', 'enum-2'],
            'schema': {
                'type': 'string'
            }
        },{
            'required': True,
            'in': 'query',
            'name': 'mock_name_3',
            'description': '{ 1. mock description }, { 2. mock documentation for field info 3 }',
            'enum': ['enum-1', 'enum-2'],
            'schema': {
                'type': 'string'
            }
        },{
            'in': 'query',
            'name': 'mock_name_4',
            'description': 'mock description',
            'schema':{
                'description': 'mock description',
                'type': 'string',
                'enum': ['enum-1', 'enum-2'],
            }
        }]
        self.assertEqual(par_array_expected, par_array_actual)
        self.assertEqual(self.new_url_expected, new_url_actual)

    def test_process_delete_request(self):
        # case 1: create parameter array using field information of parameters for 
        # delete operation in swagger 2.0 
        params = [self.field_info_mock_1, self.field_info_mock_4]
        spec = ApiSwaggerParaHandler()
        par_array_actual, new_url_actual = self.api_meta2spec.process_delete_request( self.url, params, self.type_dict, {}, {}, False, spec)
        par_array_expected = [{
            'required': True,
            'in': 'path',
            'name': 'mock_name_1',
            'description': '{ 1. mock description }, { 2. mock documentation for field info 1 }',
            'type': 'string',
            'enum' :['enum-1', 'enum-2']
        }, {
            'required': True,
            'in': 'query',
            'name': 'mock_name_4',
            'description': '{ 1. mock description }, { 2. mock documentation for field info 4 }',
            'type': 'string',
            'enum': ['enum-1', 'enum-2']
        }]
        self.assertEqual(par_array_expected, par_array_actual)
        self.assertEqual(self.new_url_expected, new_url_actual)

        # case 2: create parameter array using field information of parameters for 
        # delete operation in openAPI 3.0
        spec = ApiOpenapiParaHandler()
        par_array_actual, new_url_actual = self.api_meta2spec.process_delete_request( self.url, params, self.type_dict, {}, {}, False, spec)
        par_array_expected = [{
            'required': True,
            'in': 'path',
            'name': 'mock_name_1',
            'description': '{ 1. mock description }, { 2. mock documentation for field info 1 }',
            'enum' :['enum-1', 'enum-2'],
            'schema':{
                'type': 'string'
            }
        },{
            'required': True,
            'in': 'query',
            'name': 'mock_name_4',
            'description': '{ 1. mock description }, { 2. mock documentation for field info 4 }',
            'enum': ['enum-1', 'enum-2'],
            'schema':{
                'type': 'string'
            }
        }]
        self.assertEqual(par_array_expected, par_array_actual)
        self.assertEqual(self.new_url_expected, new_url_actual)


if __name__ == '__main__':
    unittest.main()