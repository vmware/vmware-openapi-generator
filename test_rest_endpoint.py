import unittest
from unittest import mock 
from lib.rest_endpoint.rest_type_handler import RestTypeHandler
from lib.rest_endpoint.rest_url_processing import RestUrlProcessing
from lib.rest_endpoint.rest_metamodel2spec import RestMetamodel2Spec
from lib.rest_endpoint.swagger2.rest_swagger_parameter_handler import RestSwaggerParaHandler
from lib.rest_endpoint.oas3.rest_openapi_parameter_handler import RestOpenapiParaHandler

class TestRestTypeHandler(unittest.TestCase):

    rest_tphandler = RestTypeHandler()

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
        enum_dict = {}
        type_dict = {}
        new_prop = {}
        self.rest_tphandler.visit_generic(generic_instantiation_mock, new_prop, type_dict, structure_dict, enum_dict, '#/definitions/', False )
        new_prop_expected = {'type': 'array', 'uniqueItems': True, 'items': {'type': 'date-time'}}
        self.assertEqual(new_prop_expected, new_prop)

        # case 2: when generic instantiation type is 'OPTIONAL' and category is 'BUILT-IN'
        generic_instantiation_mock.generic_type = 'OPTIONAL'
        enum_dict = {}
        type_dict = {}
        new_prop = {}
        self.rest_tphandler.visit_generic(generic_instantiation_mock, new_prop, type_dict, structure_dict, enum_dict, '#/definitions/', False )
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
        enum_dict = {}
        type_dict = {}
        new_prop = {}
        self.rest_tphandler.visit_generic(generic_instantiation_mock, new_prop, type_dict, structure_dict, enum_dict, '#/definitions/', False )
        new_prop_expected = {'type': 'array', 'items': {'$ref': '#/definitions/com.vmware.package.mock'}}
        self.assertEqual(new_prop_expected, new_prop)

        # case 4: when generic instantiation type is 'MAP', map key and value type is 'BUILTIN'
        generic_instantiation_element_type_mock = mock.Mock() 
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
        enum_dict = {}
        type_dict = {}
        new_prop = {}
        self.rest_tphandler.visit_generic(generic_instantiation_mock, new_prop, type_dict, structure_dict, enum_dict, '#/definitions/', False )
        new_prop_expected = {
            'type': 'array', 
            'items': {
                'type': 'object', 
                'properties': {
                    'key': {'type': 'integer'}, 
                    'value': {'type': 'integer'}
                    }
                }
            }
        self.assertEqual(new_prop_expected, new_prop)

class TestRestUrlProcessing(unittest.TestCase):
    
    rest_url_process = RestUrlProcessing()

    def test_contains_rm_annotation(self):
        # case 1: metadata of the service operation contains request mapping
        service_info_mock = mock.Mock()
        operation_info_mock_1 = mock.Mock()
        operation_info_mock_1.metadata = { 'RequestMapping' : 'MockObject'}
        service_info_mock.operations = { 
                                        'opertionMockKey1': operation_info_mock_1
                                       }
        '''                               
        The service info object for the test case looks like:
        ServiceInfo (operations = {
            'opertionMockKey1': OperationInfo (metadata = {
                'RequestMapping' : ElementMap()
            })
        })
        '''
        bool_value_expected = self.rest_url_process.contains_rm_annotation(service_info_mock)
        bool_value_actual = True
        self.assertEqual(bool_value_expected, bool_value_actual)

        # case 2: metadata of the service operation does not contain request mapping
        operation_info_mock_1.metadata = { 'MockMetadataKey' : 'MockObject'}
        bool_value_expected = self.rest_url_process.contains_rm_annotation(service_info_mock)
        bool_value_actual = False
        self.assertEqual(bool_value_expected, bool_value_actual)
    
    def test_find_string_element_value(self):
        # extract path variable name from element value object
        element_value_mock = mock.Mock()
        element_value_mock.string_value = 'MockPathVariableName'
        path_variable_expected = self.rest_url_process.find_string_element_value(element_value_mock)
        path_variable_actual = 'MockPathVariableName'
        self.assertEqual(path_variable_expected, path_variable_actual)

    def test_find_url_method(self):
        # case 1: url and method = none is returned
        operation_info_mock = mock.Mock()
        element_map_mock = mock.Mock()
        element_value_mock = mock.Mock()
        element_value_mock.string_value = 'MockPathVariableName'
        element_method_mock = mock.Mock()
        element_method_mock.string_value = 'MockMethodName'
        element_params_mock = mock.Mock()
        element_params_mock.string_value = 'MockParamsName'
        element_map_mock.elements = {
            'value' : element_value_mock,
        }
        operation_info_mock.metadata = {
            'RequestMapping' : element_map_mock
        }
        url_expected, method_expected = self.rest_url_process.find_url_method(operation_info_mock)
        url_actual = 'MockPathVariableName'
        method_actual = None
        self.assertEqual(url_expected, url_actual)
        self.assertEqual(method_expected, method_actual)

        # case 2: url with path parameters and method is returned
        element_map_mock.elements = {
            'value' : element_value_mock,
            'method' : element_method_mock,
            'params' : element_params_mock
        }
        '''
        Operation info object for the test case is as follows: 
        OperationInfo (metadata = {
            'RequestMapping' : ElementMap ( elements = {
                'value' : ElementValue( string_value = 'MockPathVariableName'),
                'method' : ElementValue( string_value = 'MockMethodName'),
                'params' : ElementValue( string_value = 'MockParamsName')
            })
        })
        '''
        url_expected, method_expected = self.rest_url_process.find_url_method(operation_info_mock)
        url_actual = 'MockPathVariableName?MockParamsName'
        method_actual = 'MockMethodName'
        self.assertEqual(url_expected, url_actual)
        self.assertEqual(method_expected, method_actual)

class TestRestMetamodel2Spec(unittest.TestCase):

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
    field_info_mock_2.metadata = {'metadata_key' :  element_map_mock}
    field_info_mock_2.documentation = 'mock documentation for field info 2'
    field_info_mock_2.type = field_info_type
    params = [field_info_mock_1, field_info_mock_2]

    url = '/package/mock-1/{mock}'
    type_dict = {
        'com.vmware.package.mock' : { 
            'description' : 'mock description',
            'type': 'string',
            'enum' :['enum-1', 'enum-2']
        }
    }
    new_url_expected = '/package/mock-1/{mock_name_1}'

    rest_meta2spec = RestMetamodel2Spec()

    def test_process_put_post_patch_request(self):
        # case 1: create parameter array using field information of parameters for
        # put, post, patch operations in swagger 2.0 
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
            )
            FieldInfo(name = 'mock_name_2', documentation = 'mock documentation for field info 2',
            type = Type(category = 'USER_DEFINED', 
            user_defined_type = UserDefinedType( resource_type = 'com.vmware.vapi.structure', resource_id = 'com.vmware.package.mock')
                ), metadata = {
                    'metadata_key' : ElementMap( elements = {
                        'value': ElementValue(string_value = 'mock')
                    })
            )
        ]
        '''
        spec = RestSwaggerParaHandler()
        par_array_actual, new_url_actual = self.rest_meta2spec.process_put_post_patch_request( self.url, 'com.vmware.package.mock', 
                                                                                        'mock_operation_name', self.params, 
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
            'required': True,
            'schema': {
                '$ref': '#/definitions/com.vmware.package.mock_mock_operation_name'
            }
        }]
        
        self.assertEqual(par_array_expected, par_array_actual)
        self.assertEqual(self.new_url_expected, new_url_actual)

        # case 2: create parameter array using field information of parameters for
        # put, post, patch operations in openAPI 3.0
        spec = RestOpenapiParaHandler()
        par_array_actual, new_url_actual = self.rest_meta2spec.process_put_post_patch_request(self.url, 'com.vmware.package.mock', 
                                                                                        'mock_operation_name', self.params, 
                                                                                        self.type_dict, {}, {}, False, spec)
        par_array_expected = [{
            'required': True,
            'in': 'path',
            'name': 'mock_name_1',
            'description': '{ 1. mock description }, { 2. mock documentation for field info 1 }',
            'enum' :['enum-1', 'enum-2'],
            'schema':{
                'type': 'string'
            }
        }, {
            '$ref': '#/components/requestBodies/com.vmware.package.mock_mock_operation_name'
        }]
       
        self.assertEqual(par_array_expected, par_array_actual)
        self.assertEqual(self.new_url_expected, new_url_actual)


    def test_process_get_request(self):
        # case 1: create parameter array using field information of parameters for 
        # get operation in swagger 2.0 
        spec = RestSwaggerParaHandler()
        par_array_actual, new_url_actual = self.rest_meta2spec.process_get_request( self.url, self.params, 
                                                                            self.type_dict, {}, {}, False, spec)
        par_array_expected = [{
            'required': True,
            'in': 'path',
            'name': 'mock_name_1',
            'description': '{ 1. mock description }, { 2. mock documentation for field info 1 }',
            'type': 'string',
            'enum' :['enum-1', 'enum-2']
        }, {
            'in': 'query',
            'name': 'mock_name_2',
            'description': 'mock description',
            'type': 'string',
            'enum' :['enum-1', 'enum-2'],
            'required': True
        }]
        self.assertEqual(par_array_expected, par_array_actual)
        self.assertEqual(self.new_url_expected, new_url_actual)

        # case 2: create parameter array using field information of parameters for 
        # get operation in openAPI 3.0
        spec = RestOpenapiParaHandler()
        par_array_actual, new_url_actual = self.rest_meta2spec.process_get_request(self.url, self.params, 
                                                                            self.type_dict, {}, {}, False, spec)
        par_array_expected = [{
            'required': True,
            'in': 'path',
            'name': 'mock_name_1',
            'description': '{ 1. mock description }, { 2. mock documentation for field info 1 }',
            'enum' :['enum-1', 'enum-2'],
            'schema':{
                'type': 'string'
            }
        }, {
            'in': 'query',
            'name': 'mock_name_2',
            'description': 'mock description',
            'schema':{
                'description': 'mock description',
                'type': 'string',
                'enum': ['enum-1', 'enum-2']
            }
        }]
        self.assertEqual(par_array_expected, par_array_actual)
        self.assertEqual(self.new_url_expected, new_url_actual)


    def test_process_delete_request(self):
        # case 1: create parameter array using field information of parameters for 
        # delete operation in swagger 2.0 
        spec = RestSwaggerParaHandler()
        par_array_actual, new_url_actual = self.rest_meta2spec.process_delete_request(self.url, self.params, self.type_dict,
                                                                                {}, {}, False, spec)
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
            'name': 'mock_name_2',
            'description': '{ 1. mock description }, { 2. mock documentation for field info 2 }',
            'type': 'string',
            'enum' :['enum-1', 'enum-2']
        }]
        self.assertEqual(par_array_expected, par_array_actual)
        self.assertEqual(self.new_url_expected, new_url_actual)

        # case 2: create parameter array using field information of parameters for 
        # delete operation in openAPI 3.0 
        spec = RestOpenapiParaHandler()
        par_array_actual, new_url_actual = self.rest_meta2spec.process_delete_request(self.url, self.params, self.type_dict,
                                                                                {}, {}, False, spec)
        par_array_expected = [{
            'required': True,
            'in': 'path',
            'name': 'mock_name_1',
            'description': '{ 1. mock description }, { 2. mock documentation for field info 1 }',
            'enum' :['enum-1', 'enum-2'],
            'schema':{
                'type': 'string'
            }
        }, {
            'required': True,
            'in': 'query',
            'name': 'mock_name_2',
            'description': '{ 1. mock description }, { 2. mock documentation for field info 2 }',
            'enum' :['enum-1', 'enum-2'],
            'schema':{
                'type': 'string'
            }
        }]
        self.assertEqual(par_array_expected, par_array_actual)
        self.assertEqual(self.new_url_expected, new_url_actual)


if __name__ == '__main__':
    unittest.main()