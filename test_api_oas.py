import unittest
from unittest import mock 
from lib import utils
from lib.api_endpoint.oas3.api_openapi_parameter_handler import ApiOpenapiParaHandler
from lib.api_endpoint.oas3.api_openapi_response_handler import ApiOpenapiRespHandler
from lib.api_endpoint.oas3.api_openapi_final_path_processing import ApiOpenapiPathProcessing
from lib.api_endpoint.oas3.api_metamodel2openapi import ApiMetamodel2Openapi

class TestApiOpenapiParaHandler(unittest.TestCase):

    user_defined_type_mock = mock.Mock()
    user_defined_type_mock.resource_type = 'com.vmware.vapi.structure'
    user_defined_type_mock.resource_id = 'com.vmware.package.mock-1'

    generic_instantiation_element_type_mock = mock.Mock() 
    generic_instantiation_element_type_mock.category = 'USER_DEFINED'
    generic_instantiation_element_type_mock.user_defined_type = user_defined_type_mock
    generic_instantiation_mock = mock.Mock()
    generic_instantiation_mock.generic_type = 'OPTIONAL'
    generic_instantiation_mock.element_type = generic_instantiation_element_type_mock

    field_info_mock = mock.Mock()
    field_info_type = mock.Mock()
    field_info_type.category = 'GENERIC'
    field_info_type.generic_instantiation = generic_instantiation_mock
    field_info_mock.type = field_info_type
    field_info_mock.documentation = 'Mock Description for Field Info Object'
    field_info_mock.name = 'fieldInfoMockName'
    structure_info_mock = mock.Mock()
    structure_info_mock.fields = [field_info_mock]
    structure_dict = {
        'com.vmware.package.mock-1': structure_info_mock
    }
    enum_dict = {}
    api_openapi_parahandler = ApiOpenapiParaHandler()

    def test_convert_field_info_to_swagger_parameter(self):
        # generic construction of parameter object (dictionary) using field info of path and query parameters
        type_dict = {
            'com.vmware.package.mock-1' : { 
                'description' : 'Mock Description for Type Object',
                'type': 'Mock-Type'
            }
        }
        parameter_obj_actual = self.api_openapi_parahandler.convert_field_info_to_swagger_parameter('path', self.field_info_mock, 
                                                                            type_dict, self.structure_dict, 
                                                                            self.enum_dict, False)                   
        parameter_obj_expected = {
            'required': False,
            'in': 'path',
            'name': 'fieldInfoMockName',
            'description': '{ 1. Mock Description for Type Object }, { 2. Mock Description for Field Info Object }',
            'schema': {'type': 'Mock-Type'}
        }                        
        self.assertEqual(parameter_obj_expected, parameter_obj_actual)
    
    def test_wrap_body_params(self):
        # validate parameter object by creating json wrappers around body object
        type_dict = {
            'com.vmware.package.mock-1' : {}
        }
        body_param_list = [self.field_info_mock]
        parameter_obj_actual = self.api_openapi_parahandler.wrap_body_params('com.vmware.package.mock-1', 'mockOperationName', 
                                                                        body_param_list, type_dict, self.structure_dict, 
                                                                        self.enum_dict, False)
        parameter_obj_expected = {'$ref': '#/components/requestBodies/com.vmware.package.mock-1_mockOperationName'}
        self.assertEqual(parameter_obj_expected, parameter_obj_actual)
        type_dict_expected = {
            'com.vmware.package.mock-1': {},
            'requestBodies': {
                'com.vmware.package.mock-1_mockOperationName':{
                    'content':{
                        'application/json':{
                            'schema':{
                                '$ref': '#/components/schemas/com.vmware.package.mock-1_mockOperationName'
                            }
                        }
                    }
                }
            },
            'com.vmware.package.mock-1_mockOperationName':{
                'required': False,
                '$ref': '#/components/schemas/com.vmware.package.mock-1',
                'description': 'Mock Description for Field Info Object'
            }
        }
        self.assertEqual(type_dict, type_dict_expected)
    
    def test_flatten_query_param_spec(self):
        # case 1: parameter object takes reference from type_dict key
        # case 1.1: type dict reference value contains properties
        # case 1.1.1: property value inside type_dict is defined in-place
        query_info_mock = mock.Mock()
        query_info_type = mock.Mock()
        query_info_type.category = 'USER_DEFINED'
        query_info_type.user_defined_type = self.user_defined_type_mock
        query_info_mock.type = query_info_type
        query_info_mock.documentation = 'QueryMockDescription'
        query_info_mock.name = 'QueryParameterMockName'
        type_dict = {
            'com.vmware.package.mock-1' : {  #type_ref
                'properties': { 
                    'property-name': {   #property_value
                        'type': 'array',
                        'items': {
                            '$ref': '#/components/schemas/com.vmware.package.mock.items'
                        },
                        'description' : 'mock property description'
                    }
                }
            },
            'com.vmware.package.mock.items': {
                'type': 'string',
                'description': 'some mock description'
            }
        }
        structure_dict = {}
        par_array_actual = self.api_openapi_parahandler.flatten_query_param_spec(query_info_mock, type_dict, 
                                                                        structure_dict, self.enum_dict, False)
        par_array_expected = [
            {
                'in':'query',
                'name': 'property-name',
                'schema': {
                    'type': 'array',
                    'items': {
                        'type': 'string'
                    }
                },
                'description': 'mock property description'
            }
        ]
        self.assertEqual(par_array_expected, par_array_actual)

        # type reference dictionary is empty
        type_dict = {
            'com.vmware.package.mock-1' : None
        }
        par_array_actual = self.api_openapi_parahandler.flatten_query_param_spec(query_info_mock, type_dict, 
                                                                        structure_dict, self.enum_dict, False)
        par_array_expected = None
        self.assertEqual(par_array_expected, par_array_actual)

        # case 1.1.2: property value is referenced from type_dict
        type_dict = {
            'com.vmware.package.mock-1' : {  #type_ref
                'properties': { 
                    'property-name': {   #property_value
                        '$ref': '#/components/schemas/com.vmware.package.mock.property'
                    },
                    'property-name-mock': {}
                },
                'required': ['property-name']
            },
            'com.vmware.package.mock.property': { #prop_obj
                'type': 'object',
                'enum': ['enum-value-1, enum-value-2'],
                'description': 'mock property description'

            }
        }
        par_array_actual = self.api_openapi_parahandler.flatten_query_param_spec(query_info_mock, type_dict, 
                                                          structure_dict, self.enum_dict, False)
        par_array_expected = [
            {
                'in':'query',
                'name': 'property-name',
                'schema':{
                    'type': 'object',
                    'enum': ['enum-value-1, enum-value-2'],
                    'description': 'mock property description'
                },
                'required': True
            },
            {
                'in': 'query',
                'name': 'property-name-mock',
                'schema': {},
                'required': False
            }
        ]
        self.assertEqual(par_array_expected, par_array_actual)

        # case 1.2: type dict reference value does not contain properties
        type_dict = {
            'com.vmware.package.mock-1' : {  #type_ref
                'description' : 'mock description',
                'type': 'string',
                'enum': ['enum-1', 'enum-2']
            }
        }
        par_array_actual = self.api_openapi_parahandler.flatten_query_param_spec(query_info_mock, type_dict, 
                                                          structure_dict, self.enum_dict, False)
        par_array_expected = [
            {
                'in':'query',
                'name': 'QueryParameterMockName',
                'description': 'mock description',
                'schema':{
                    'description': 'mock description',
                    'type': 'string',
                    'enum': ['enum-1', 'enum-2']
                }
            }
        ]
        self.assertEqual(par_array_expected, par_array_actual)

        # case 2: parameter object does not take reference from type dict key
        query_info_mock = mock.Mock()
        query_info_type = mock.Mock()
        query_info_type.category = 'BUILTIN'
        query_info_type.builtin_type = 'string'
        query_info_mock.type = query_info_type
        query_info_mock.documentation = 'QueryMockDescription'
        query_info_mock.name = 'QueryParameterMockName'
        type_dict = {}
        par_array_actual = self.api_openapi_parahandler.flatten_query_param_spec(query_info_mock, type_dict, 
                                                          structure_dict, self.enum_dict, False)
        par_array_expected = [
            {
                'in':'query',
                'name': 'QueryParameterMockName',
                'description': 'QueryMockDescription',
                'required': True,
                'schema': {
                    'type': 'string'
                }
            }
        ]
        self.assertEqual(par_array_expected, par_array_actual)

class TestApiOpenapiRespHandler(unittest.TestCase):

    def test_populate_response_map(self):
        # get response map corresponding to errors in operation information
        user_defined_type_mock = mock.Mock()
        user_defined_type_mock.resource_type = 'com.vmware.vapi.structure'
        user_defined_type_mock.resource_id = 'com.vmware.package.mock'
        output_mock =  mock.Mock()
        output_mock_type = mock.Mock()
        output_mock_type.category = 'USER_DEFINED'
        output_mock_type.user_defined_type = user_defined_type_mock
        output_mock.documentation = 'mock output description'
        output_mock.type = output_mock_type
        error_mock =  mock.Mock()
        error_mock.structure_id = 'com.vmware.vapi.std.errors.not_found'
        error_mock.documentation = 'mock error description'
        errors = [error_mock]
        type_dict = {
                'com.vmware.vapi.std.errors.not_found' : {},
                'com.vmware.package.mock' : { 
                    'description' : 'mock description',
                    'type': 'string',
                    'enum': ['enum-1', 'enum-2']
                }
            }
        '''
        Mock parameters : output and errors
        output( documentation = 'mock output description', 
        type = Type( category = 'USER_DEFINED', 
        user_defined_type = UserDefinedType( resource_id = 'com.vmware.package.mock', 
        resource_type = 'com.vmware.vapi.structure')))

        errors = [error( documentation = 'mock error description', structure_id = 'com.vmware.vapi.std.errors.not_found')]
        '''
        structure_info_mock = mock.Mock()
        metadata_mock = mock.Mock()
        element_value_mock = mock.Mock()
        element_value_mock.string_value = '404'
        metadata_mock.elements = { 'code' : element_value_mock}
        structure_info_mock.metadata = { 'Response' : metadata_mock}
        structures = { 'com.vmware.mock.structure' : structure_info_mock  }
        structures_obj = mock.Mock()
        structures_obj.structures = structures
        info_mock = mock.Mock()
        info_mock.packages = { 'com.vmware.vapi.std.errors' : structures_obj}
        component_svc_obj = mock.Mock()
        component_svc_obj.info = info_mock
        component_svc_mock = { 'com.vmware.vapi' : component_svc_obj}
        '''
        Mock parameter : component_svc
        component_svc = { 'com.vmware.vapi' : Component( info = ComponentInfo(
            packages = {'com.vmware.vapi.std.errors' : StructureInfo (structures = {
                'com.vmware.mock.structure' : StructureInfo(metadata = {
                    'Response' : { ElementMap( elements = ElementValue( string_value = '404'))}
                })
            })}
        ))}
        '''
        op_metadata = {'Response': metadata_mock}
        http_error_map = utils.HttpErrorMap(component_svc_mock)
        api_openapi_resphandler = ApiOpenapiRespHandler()
        response_map_actual = api_openapi_resphandler.populate_response_map(output_mock, errors, 
                                    http_error_map,type_dict, {}, {}, 'mock-service-id',
                                   'mock-operation-id', op_metadata, False)
        
        response_map_expected = {
            404: {
                'description': 'mock output description',
                'content':{
                    'application/json':{
                        'schema':{
                            '$ref': '#/components/schemas/com.vmware.package.mock'
                        }
                    }
                }
            },
            500: {
                'description': 'mock error description',
                'content':{
                    'application/json':{
                        'schema':{
                            '$ref': '#/components/schemas/com.vmware.vapi.std.errors.not_found'
                        }
                    }
                }
            }
        }
        self.assertEqual(response_map_expected, response_map_actual)

class TestApiOpenapiPathProcessing(unittest.TestCase):

    api_openapi_path = ApiOpenapiPathProcessing()

    def test_remove_query_params(self):
        # case 1: Absolute Duplicate paths, which will remain unchanged
        path_dict = {
            'mock/path1?action=mock_action':{
                'post':{
                    'parameters' : [] # parameters attr is always created even if there isn't any
                }
            },
            'mock/path1':{
                'post':{
                }
            }
        }
        path_dict_expected = {
            'mock/path1?action=mock_action':{
                'post':{
                    'parameters' : []
                }
            },
            'mock/path1':{
                'post':{
                }
            }
        }
        self.api_openapi_path.remove_query_params(path_dict)
        self.assertEqual(path_dict, path_dict_expected)

        # case 2: Partial Duplicate, adding the Operations of the new duplicate path 
        # to that of the existing path based on method type
        # case 2.1: only one of them as query parameter
        path_dict = {
            'mock/path1?action=mock_action':{
                'post':{
                    'parameters' : []
                }
            },
            'mock/path1':{
                'get':{
                    'parameters' : []
                }
            }
        }
        path_dict_expected = {
            'mock/path1': {
                'post': {
                    'parameters': [
                        {
                            'name': 'action', 
                            'in': 'query', 
                            'description':'action=mock_action', 
                            'required': True, 
                            'schema':{
                                'type': 'string', 
                                'enum': ['mock_action']
                            }
                        }
                    ]
                }, 
                'get': {
                    'parameters' : []
                }
            }
        }
        self.api_openapi_path.remove_query_params(path_dict)
        self.assertEqual(path_dict, path_dict_expected)

        # case 2.2: only one of them as query parameter without specified enum value
        path_dict = {
            'mock/path1?action': {
                'post': {
                    'parameters': []
                }
            },
            'mock/path1': {
                'get': {
                    'parameters': []
                }
            }
        }
        path_dict_expected = {
            'mock/path1': {
                'post': {
                    'parameters': [
                        {
                            'name': 'action',
                            'in': 'query',
                            'description': 'action',
                            'required': True,
                            'schema': {
                                'type': 'string'
                            }
                        }
                    ]
                },
                'get': {
                    'parameters': []
                }
            }
        }
        self.api_openapi_path.remove_query_params(path_dict)
        self.assertEqual(path_dict, path_dict_expected)

        # case 2.3: both of them have query parameter
        path_dict = {
            'mock/path1?action=mock_action_1':{
                'post':{
                    'parameters' : []
                }
            },
            'mock/path1?action=mock_action_2':{
                'get':{
                    'parameters' : []
                }
            }
        }
        path_dict_expected = {
            'mock/path1': {
                'get': {
                    'parameters': [{
                        'name': 'action',
                        'in': 'query',
                        'description': 'action=mock_action_2',
                        'required': True,
                        'schema':{
                            'type': 'string',
                            'enum': ['mock_action_2']
                        }
                    }]
                },
                'post': {
                    'parameters': [{
                        'name': 'action',
                        'in': 'query',
                        'description': 'action=mock_action_1',
                        'required': True,
                        'schema':{
                            'type': 'string',
                            'enum': ['mock_action_1']
                        }
                    }]
                }
            }
        }
        self.api_openapi_path.remove_query_params(path_dict)
        self.assertEqual(path_dict, path_dict_expected)

        # case 3: QueryParameters are fixed and method types are same
        path_dict = {
            'mock/path1?action=mock_action_1':{
                'post':{
                    'parameters' : []
                }
            },
            'mock/path1?action=mock_action_2':{
                'post':{
                    'parameters' : []
                }
            }
        }
        path_dict_expected = {
            'mock/path1?action=mock_action_2': {
                'post': {
                    'parameters': []
                }
            },
            'mock/path1': {
                'post': {
                    'parameters': [{
                        'name': 'action',
                        'in': 'query',
                        'description': 'action=mock_action_1',
                        'required': True,
                        'schema':{
                            'type': 'string',
                            'enum': ['mock_action_1']
                        }
                    }]
                }
            }
        }
        self.api_openapi_path.remove_query_params(path_dict)
        self.assertEqual(path_dict, path_dict_expected)

class TestApiMetamodel2Openapi(unittest.TestCase):

    api_meta2openapi = ApiMetamodel2Openapi()

    def test_post_process_path(self):
        # case 1: adding header parameter in list of parameters 
        # if path equals '/com/vmware/cis/session' and method is 'post
        # Also allow invocation of $tasks operation
        path_obj = {
            'path': '/com/vmware/cis/session',
            'method': 'post',
            'operationId': 'MockOperationId$task',
        }
        self.api_meta2openapi.post_process_path(path_obj)
        path_obj_expected = {
            'path': '/com/vmware/cis/session?vmw-task=true',
            'method': 'post',
            'operationId': 'MockOperationId$task',
            'parameters': [{
                'in': 'header',
                'required': True,
                'type': 'string',
                'name': 'vmware-use-header-authn',
                'description': 'Custom header to protect against CSRF attacks in browser based clients',
                'schema':{'type': 'string'}
            }]
        }
        self.assertEqual(path_obj, path_obj_expected)

        # case 2: If above conditions are not satisfied, path object remains unaltered 
        path_obj = {
            'path': '/package/mock-1/{mock}/mock?key=value',
            'method': 'post',
            'operationId': 'MockOperationId',
        }
        path_obj_expected = path_obj
        self.api_meta2openapi.post_process_path(path_obj)
        self.assertEqual(path_obj, path_obj_expected)

if __name__ == '__main__':
    unittest.main()