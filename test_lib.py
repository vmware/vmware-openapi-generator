import unittest
from unittest import mock
import vmsgen
from lib import utils
from lib import establish_connection as connection
from lib import dictionary_processing as dict_processing
from lib.dictionary_processing import ServiceType
from lib.path_processing import PathProcessing
from lib.rest_endpoint.rest_navigation_handler import RestNavigationHandler
from lib.url_processing import UrlProcessing
from lib.type_handler_common import TypeHandlerCommon

class TestInputs(unittest.TestCase):

    def test_get_input_params(self):
        # case 1.1: SSL is secure
        test_args = ['vmsgen', '-vc', 'v_url']
        ssl_verify_expected = True
        with mock.patch('sys.argv', test_args):
            _, _, _, ssl_verify_actual, _, _, _, _, _, _, = connection.get_input_params()
        self.assertEqual(ssl_verify_expected, ssl_verify_actual)

        # case 1.2: SSL is insecure
        test_args = ['vmsgen', '-vc', 'v_url', '-k']
        ssl_verify_expected = False
        with mock.patch('sys.argv', test_args):
            _, _, _, ssl_verify_actual, _, _, _, _, _, _, = connection.get_input_params()
        self.assertEqual(ssl_verify_expected, ssl_verify_actual)

        # case 2.1: tag separator option (default)
        test_args = ['vmsgen', '-vc', 'v_url', '-k']
        tag_separator_expected = '/'
        with mock.patch('sys.argv', test_args):
            _, _, _, _, _, _, _, _, tag_separator_actual, _, = connection.get_input_params()
        self.assertEqual(tag_separator_expected, tag_separator_actual)

        # case 2.2: tag separator option
        expected = '_'
        test_args = ['vmsgen', '-vc', 'v_url', '-s', expected]
        with mock.patch('sys.argv', test_args):
            _, _, _, _, _, _, _, _, tag_separator_actual, _, = connection.get_input_params()
        self.assertEqual(expected, tag_separator_actual)

        # case 3.1: operation id option is FALSE
        test_args = ['vmsgen', '-vc', 'v_url', '-k']
        generate_op_id_expected = False
        with mock.patch('sys.argv', test_args):
            _, _, _, _, _, _, _, generate_op_id_actual, _, _, = connection.get_input_params()
        self.assertEqual(generate_op_id_expected, generate_op_id_actual)

        # case 3.1: operation id option is TRUE
        test_args = ['vmsgen', '-vc', 'v_url', '-k', '-uo']
        generate_op_id_expected = True
        with mock.patch('sys.argv', test_args):
            _, _, _, _, _, _, _, generate_op_id_actual, _, _, = connection.get_input_params()
        self.assertEqual(generate_op_id_expected, generate_op_id_actual)

        # case 4.1: generate metamodel option is FALSE
        test_args = ['vmsgen', '-vc', 'v_url', '-k']
        generate_metamodel_expected = False
        with mock.patch('sys.argv', test_args):
            _, _, _, _, _, generate_metamodel_actual, _, _, _, _, = connection.get_input_params()
        self.assertEqual(generate_metamodel_expected, generate_metamodel_actual)

        # case 4.1: generate metamodel option is TRUE
        test_args = ['vmsgen', '-vc', 'v_url', '-k', '-c']
        generate_metamodel_expected = True
        with mock.patch('sys.argv', test_args):
            _, _, _, _, _, generate_metamodel_actual, _, _, _, _, = connection.get_input_params()
        self.assertEqual(generate_metamodel_expected, generate_metamodel_actual)
        
        # case 5.1: swagger specification is default i.e openAPI 3.0
        test_args = ['vmsgen', '-vc', 'v_url', '-k']
        swagger_specification_expected = '3'
        with mock.patch('sys.argv', test_args):
            _, _, _, _, _, _, swagger_specification_actual, _, _, _, = connection.get_input_params()
        self.assertEqual(swagger_specification_expected, swagger_specification_actual)

        # case 5.2: swagger specification is swagger 2.0
        test_args = ['vmsgen', '-vc', 'v_url', '-k', '-oas' , '2']
        swagger_specification_expected = '2'
        with mock.patch('sys.argv', test_args):
            _, _, _, _, _, _, swagger_specification_actual, _, _, _, = connection.get_input_params()
        self.assertEqual(swagger_specification_expected, swagger_specification_actual)

        # case 6.1: mixed option is TRUE
        test_args = ['vmsgen', '-vc', 'v_url', '-k', '-mixed']
        mixed_expected = True
        with mock.patch('sys.argv', test_args):
            _, _, _, _, _, _, _, _, _, mixed_actual = connection.get_input_params()
        self.assertEqual(mixed_expected, mixed_actual)

        # case 6.1: mixed option is FALSE
        test_args = ['vmsgen', '-vc', 'v_url', '-k']
        mixed_expected = False
        with mock.patch('sys.argv', test_args):
            _, _, _, _, _, _, _, _, _, mixed_actual = connection.get_input_params()
        self.assertEqual(mixed_expected, mixed_actual)


class TestDictionaryProcessing(unittest.TestCase):

    def test_get_service_url_from_service_id(self):
        base_url = "https://vcip/rest"
        service_id = "com.vmware.vcenter.ovf.import_flag"
        service_url_expected = "https://vcip/rest/com/vmware/vcenter/ovf/import-flag"
        service_url_actual = dict_processing.get_service_url_from_service_id(base_url, service_id)
        self.assertEqual(service_url_expected, service_url_actual)

    def test_get_service_path_from_service_url(self):
        base_url = "https://vcip/rest"
        # case 1 : service url starts with base url
        service_url = "https://vcip/rest/com/vmware/package-mock/mock"
        service_url_expected = "/com/vmware/package-mock/mock"
        service_url_actual = dict_processing.get_service_path_from_service_url(service_url, base_url)
        self.assertEqual(service_url_expected, service_url_actual)

        # case 2 : service url does not start with base url
        service_url = "https://vcip/endpoint/com/vmware/package-mock/mock"
        service_url_expected = "https://vcip/endpoint/com/vmware/package-mock/mock"
        service_url_actual = dict_processing.get_service_path_from_service_url(service_url, base_url)
        self.assertEqual(service_url_expected, service_url_actual)
    
    def test_get_paths_inside_metamodel(self):
        #case 1: https methods ('put', 'post', 'patch', 'get', 'delete') not in metadata.keys
        operation_info_mock = mock.Mock()
        operation_info_mock.metadata = { 
                        'Mock-key-1.1' : {}
                        }
        service_info_mock = mock.Mock()
        service_info_mock.operations = {
                    'mock-key-1': operation_info_mock
                     }
        service = 'com.vmware.package-mock-1.mock.mock'
        service_dict = {
            'com.vmware.package-mock-1.mock.mock': service_info_mock
        }
        '''
        Structure of key-value pair in service_dict
        service_dict = {
            'com.vmware.package-mock-1.mock.mock':  
                ServiceInfo(
                operations = {
                    'mock-key-1': OperationInfo(metadata = {
                                        'Mock-key-1.1' : {}
                    })
                })
            }
        '''
        path_list_expected = []
        service_type_actual, path_list_actual = dict_processing.get_paths_inside_metamodel(service, service_dict)
        self.assertEqual(ServiceType.REST, service_type_actual)
        self.assertEqual(path_list_expected, path_list_actual)

        #case 2: https methods ('put', 'post', 'patch', 'get', 'delete') in metadata.keys
        element_value_mock = mock.Mock()
        element_value_mock.string_value = 'mock_string_value'
        element_info_mock = mock.Mock()
        element_info_mock.elements = {
            'path' : element_value_mock
        }
        operation_info_mock.metadata = { 
                            'put' : element_info_mock
                            }
        service_info_mock.operations = {
                        'mock-key-1': operation_info_mock
                    }
        service = 'com.vmware.package-mock-1.mock.mock'
        service_dict = {
            'com.vmware.package-mock-1.mock.mock': service_info_mock
        }
        '''
        Structure of key-value pair in service_dict
        service_dict = {
            'com.vmware.package-mock-1.mock.mock':  
                ServiceInfo(
                operations = {
                    'mock-key-1': OperationInfo(metadata = {
                                        'put' : ElementInfo(elemets = {
                                            'path' : ElementValue(string_value = 'mock_string_value')
                                        })
                    })
                })
            }
        '''
        path_list_expected = ['mock_string_value']
        service_type_actual, path_list_actual = dict_processing.get_paths_inside_metamodel(service, service_dict)
        self.assertEqual(ServiceType.API, service_type_actual)
        self.assertEqual(path_list_expected, path_list_actual)

        # case 3: https methods ('put', 'post', 'patch', 'get', 'delete') in metadata.keys with mixed applied
        element_value_mock = mock.Mock()
        element_value_mock.string_value = 'mock_string_value'
        element_info_mock = mock.Mock()
        element_info_mock.elements = {
            'path': element_value_mock
        }
        operation_info_mock.metadata = {
            'put': element_info_mock
        }
        service_info_mock.operations = {
            'mock-key-1': operation_info_mock
        }
        service = 'com.vmware.package-mock-1.mock.mock'
        service_dict = {
            'com.vmware.package-mock-1.mock.mock': service_info_mock
        }
        '''
        Structure of key-value pair in service_dict
        service_dict = {
            'com.vmware.package-mock-1.mock.mock':  
                ServiceInfo(
                operations = {
                    'mock-key-1': OperationInfo(metadata = {
                                        'put' : ElementInfo(elemets = {
                                            'path' : ElementValue(string_value = 'mock_string_value')
                                        })
                    })
                })
            }
        '''
        path_list_expected = ['mock_string_value']
        service_type_actual, path_list_actual = dict_processing.get_paths_inside_metamodel(service, service_dict, True)
        self.assertEqual(ServiceType.API, service_type_actual)
        self.assertEqual(path_list_expected, path_list_actual)

        # case 3.1: https methods ('put', 'post', 'patch', 'get', 'delete') in metadata.keys with mixed applied
        # and RequestMapping apparent in the metadata
        element_value_mock = mock.Mock()
        element_value_mock.string_value = 'mock_string_value'
        element_info_mock = mock.Mock()
        element_info_mock.elements = {
            'path': element_value_mock
        }
        operation_info_mock.metadata = {
            'put': element_info_mock,
            'RequestMapping': {}
        }
        service_info_mock.operations = {
            'mock-key-1': operation_info_mock
        }
        service = 'com.vmware.package-mock-1.mock.mock'
        service_dict = {
            'com.vmware.package-mock-1.mock.mock': service_info_mock
        }
        '''
        Structure of key-value pair in service_dict
        service_dict = {
            'com.vmware.package-mock-1.mock.mock':  
                ServiceInfo(
                operations = {
                    'mock-key-1': OperationInfo(metadata = {
                                        'put' : ElementInfo(elemets = {
                                            'path' : ElementValue(string_value = 'mock_string_value')
                                        }),
                                        'RequestMapping' : {})
                    })
                })
            }
        '''
        path_list_expected = ['mock_string_value']
        replacement_map_expected = {service: {"mock-key-1": {"put": "mock_string_value"}}}
        replacement_map_actual = {}
        service_type_actual, path_list_actual = dict_processing.get_paths_inside_metamodel(service, service_dict, True, replacement_map_actual)
        self.assertEqual(ServiceType.MIXED, service_type_actual)
        self.assertEqual(path_list_expected, path_list_actual)
        self.assertEqual(replacement_map_expected, replacement_map_actual)

        # case 3.2: https methods ('put', 'post', 'patch', 'get', 'delete') in metadata.keys with mixed applied
        # and apparent in navigation service
        rest_navigation_handler = RestNavigationHandler("")
        rest_navigation_handler.get_service_operations = mock.MagicMock(return_value={})
        element_value_mock = mock.Mock()
        element_value_mock.string_value = 'mock_string_value'
        element_info_mock = mock.Mock()
        element_info_mock.elements = {
            'path': element_value_mock
        }
        operation_info_mock.metadata = {
            'put': element_info_mock,
        }
        service_info_mock.operations = {
            'mock-key-1': operation_info_mock
        }
        service = 'com.vmware.package-mock-1.mock.mock'
        service_dict = {
            'com.vmware.package-mock-1.mock.mock': service_info_mock
        }
        '''
        Structure of key-value pair in service_dict
        service_dict = {
            'com.vmware.package-mock-1.mock.mock':  
                ServiceInfo(
                operations = {
                    'mock-key-1': OperationInfo(metadata = {
                                        'put' : ElementInfo(elemets = {
                                            'path' : ElementValue(string_value = 'mock_string_value')
                                        }))
                    })
                })
            }
        '''
        path_list_expected = ['mock_string_value']
        replacement_map_expected = {service: {"mock-key-1": {"put": "mock_string_value"}}}
        replacement_map_actual = {}
        service_type_actual, path_list_actual = dict_processing.get_paths_inside_metamodel(service,
                                                                                           service_dict,
                                                                                           True,
                                                                                           replacement_map_actual,
                                                                                           "sample_service_url",
                                                                                           rest_navigation_handler)
        self.assertEqual(ServiceType.MIXED, service_type_actual)
        self.assertEqual(path_list_expected, path_list_actual)
        self.assertEqual(replacement_map_expected, replacement_map_actual)


    def test_add_service_urls_using_metamodel(self):
        #case 1: checking for package_dict_api{}
        service_urls_map = { 'https://vcip/rest/com/vmware/package/mock' : 'com.vmware.package.mock'}
        rest_navigation_url = 'https://vcip/rest'
        rest_navigation_handler = RestNavigationHandler(rest_navigation_url)
        rest_navigation_handler.get_service_operations = mock.MagicMock(return_value={})
        element_value_mock = mock.Mock()
        element_value_mock.string_value = '/package/mock'
        element_info_mock = mock.Mock()
        element_info_mock.elements = {
            'path' : element_value_mock
        }
        operation_info_mock = mock.Mock()
        operation_info_mock.metadata = { 
                            'put' : element_info_mock
                            }
        service_info_mock = mock.Mock()
        service_info_mock.operations = {
                        'mock-key-1': operation_info_mock
                    }
        service_dict = {
            'com.vmware.package.mock': service_info_mock
        }
        package_dict_api_expected = { 'package': ['/package/mock'] }
        package_dict_api_actual, _, = dict_processing.add_service_urls_using_metamodel(service_urls_map,service_dict,rest_navigation_handler)
        self.assertEqual(package_dict_api_expected, package_dict_api_actual)
       
        #case 2: checking for package_dict{}
        service_urls_map = { 'https://vcip/rest/vmware/com/package/mock' : 'com.vmware.package.mock'}
        element_value_mock.string_value = 'mock_string_value'
        operation_info_mock.metadata = { 
                            'mock_element_key' : element_info_mock
                            }
        package_dict_expected = {'package': ['/vmware/com/package/mock']}
        _, package_dict_actual = dict_processing.add_service_urls_using_metamodel(service_urls_map,service_dict,rest_navigation_handler)
        self.assertEqual(package_dict_expected, package_dict_actual)

        #case 3: checking for package_dict_deprecated{}
        service_urls_map = { 'https://vcip/rest/vmware/com/package/mock' : 'com.vmware.package.mock'}
        element_value_mock.string_value = '/package/mock'
        operation_info_mock.metadata = {
                            'put' : element_info_mock,
                            'RequestMapping': {}
                            }
        package_dict_deprecated_expected = {'package': ['/vmware/com/package/mock']}
        package_dict_api_expected = {'package': ['/package/mock']}
        package_dict_api_actual, package_dict_actual, package_dict_deprecated_actual, _, = dict_processing.add_service_urls_using_metamodel(service_urls_map,service_dict,rest_navigation_handler, True)

        self.assertEqual(package_dict_deprecated_expected, package_dict_deprecated_actual)
        self.assertEqual(package_dict_api_expected, package_dict_api_actual)



    def test_objectTodict(self):
        # case 1: object is of type interger
        obj_mock = 1
        expected_object = dict_processing.objectTodict(obj_mock)
        actual_object = 1
        self.assertEqual(expected_object, actual_object)

        # case 2: object is of type dict
        obj_mock = {
        'key-1': {
            'key-1.1': 'value-1.1'
            }
        }
        expected_object = dict_processing.objectTodict(obj_mock)
        self.assertEqual(expected_object, obj_mock)

        # case 3: object is of type list
        obj_mock = ['item-1', { 'key': 'value'}]
        expected_object = dict_processing.objectTodict(obj_mock)
        self.assertEqual(expected_object, obj_mock)


class TestUtils(unittest.TestCase):

    def test_is_filtered(self): 
        '''create a mock object for service info'''
        ServiceInfoMock = mock.Mock()
        ServiceInfoMock.metadata = { 'TechPreview' : {} }
        
        #case 1: enable filtering is False
        bool_value_expected = False
        bool_value_actual = utils.is_filtered(ServiceInfoMock.metadata, False)
        self.assertEqual(bool_value_expected, bool_value_actual)

        #case 2: enable filtering True
        bool_value_expected = False
        bool_value_actual = utils.is_filtered(ServiceInfoMock.metadata, True)
        self.assertEqual(bool_value_expected, bool_value_actual)

        #case 3: metadata is empty
        ServiceInfoMock.metadata = {}
        bool_value_expected = False
        bool_value_actual = utils.is_filtered(ServiceInfoMock.metadata, True)
        self.assertEqual(bool_value_expected, bool_value_actual)
       
        #case 4: enable filtering is True and metadata contains changing 
        ServiceInfoMock.metadata = { 
                'Changing' : {},
                'Proposed' : {}
            }
        bool_value_expected = True
        bool_value_actual = utils.is_filtered(ServiceInfoMock.metadata, True)
        self.assertEqual(bool_value_expected, bool_value_actual)

        # case 5: enable filtering is True and metadata does not contain 'TechPreview', 'Changing' or 'Proposed'
        ServiceInfoMock.metadata = { 
                'mock metadata key' : {}
            }
        bool_value_expected = False
        bool_value_actual = utils.is_filtered(ServiceInfoMock.metadata, True)
        self.assertEqual(bool_value_expected, bool_value_actual)
    
    def test_tags_from_service_name(self):
        # case 1: tags generation from short name
        expected = ['']
        utils.TAG_SEPARATOR = ''
        actual = utils.tags_from_service_name('three.levels.deep')
        self.assertEqual(expected, actual)

        # case 2: test tags generation from proper name
        expected = ['levels_deep']
        utils.TAG_SEPARATOR = '_'
        actual = utils.tags_from_service_name('more.than.three.levels.deep')
        self.assertEqual(expected, actual)
    
    def test_is_param_path_variable(self):
        #case 1: parameter name equals the path url placeholder
        path_param_placeholder = 'mock'
        field_info_mock = mock.Mock()
        field_info_mock.name = 'mock'
        bool_value_actual = True
        bool_value_expected = utils.is_param_path_variable(field_info_mock, path_param_placeholder)
        self.assertEqual(bool_value_expected, bool_value_actual)

        #case 2: parameter name not equals the path url placeholder
        # && parameter metadata does not contain path variable
        element_value_mock = mock.Mock()
        element_value_mock.string_value = 'mock_string_value'
        element_map_mock = mock.Mock()
        element_map_mock.elements = {'value': element_value_mock}
        field_info_mock.name = 'mock_name'
        field_info_mock.metadata = {'mock_element_key' :  element_map_mock}
        '''
        The field info structure looks like :
        FieldInfo(name = 'mock_name', metadata = {
            'mock_element_key' : ElementMap(elements = {
                'value' : ElementValue(string_value = 'mock_string_value')
            })
        })
        '''
        bool_value_actual = False
        bool_value_expected = utils.is_param_path_variable(field_info_mock, path_param_placeholder)
        self.assertEqual(bool_value_expected, bool_value_actual)

        #case 3: comparing placeholder with value of parameter elements
        path_param_placeholder = 'mock_string_value'
        field_info_mock.metadata = {'PathVariable' :  element_map_mock}
        bool_value_actual = True
        bool_value_expected = utils.is_param_path_variable(field_info_mock, path_param_placeholder)
        self.assertEqual(bool_value_expected, bool_value_actual)
    
    def test_extract_path_parameters(self):
        #case 1: parameter is a path variable
        element_value_mock = mock.Mock()
        element_value_mock.string_value = 'mock'
        element_map_mock = mock.Mock()
        element_map_mock.elements = {'value': element_value_mock}
        field_info_mock = mock.Mock()
        field_info_mock.name = 'mock_name'
        field_info_mock.metadata = {'PathVariable' :  element_map_mock}
        url = '/package/mock-1/{mock}'
        params = [field_info_mock]
        ''''
        params = [FieldInfo(name = 'mock_name', metadata = {
            'PathVariable' : ElementMap(elements = {
                'value' : ElementValue(string_value = 'mock')
            })
        })]
        ''' 
        path_params_expected = [field_info_mock]
        other_params_expected = []
        new_url_expected = '/package/mock-1/{mock_name}'
        path_params_actual, other_params_actual, new_url_actual = utils.extract_path_parameters(params, url)
        self.assertEqual(path_params_expected, path_params_actual)
        self.assertEqual(other_params_expected, other_params_actual)
        self.assertEqual(new_url_expected, new_url_actual)

        #case 2: parameter is not a path variable
        field_info_mock.metadata = {'metadata_key' :  element_map_mock}
        path_params_expected = []
        other_params_expected = [field_info_mock]
        new_url_expected = '/package/mock-1/{mock}'
        path_params_actual, other_params_actual, new_url_actual = utils.extract_path_parameters(params, url)
        self.assertEqual(path_params_expected, path_params_actual)
        self.assertEqual(other_params_expected, other_params_actual)
        self.assertEqual(new_url_expected, new_url_actual)
    
    def test_build_path(self):
        # generic mock path object creation
        path_obj_expected = {
            'tags': ['mock_tag'],
            'method': 'get',
            'path': '/com/vmware/mock_package/mock_tag',
            'summary': 'mock documentation',
            'responses': {'response code 1': {}, 'response code 2' : {} },
            'consumes': 'mock consumes',
            'produces': 'mock produces',
            'operationId': 'mock id',
            'parameters': [{'mock params':'params 1'}]
        }
        path_obj_actual = utils.build_path('com.vmware.mock_package.mock_tag', 'get', '/com/vmware/mock_package/mock_tag', 
                                  'mock documentation', [{'mock params':'params 1'}], 'mock id', 
                                  {'response code 1': {}, 'response code 2' : {} },'mock consumes', 'mock produces')
        self.assertEqual(path_obj_expected, path_obj_actual)
        
    def test_add_basic_auth(self):
        # check for adding security security attribute related to '/com/vmware/cis/session'
        path_obj = {
            'tags': ['session'],
            'method': 'post',
            'path': '/com/vmware/cis/session',
            'summary': 'mock documentation',
            'responses': {'response code 1': {}, 'response code 2' : {} },
            'consumes': 'mock consumes',
            'produces': 'mock produces',
            'operationId': 'mock id',
            'parameters': [{'mock params':'params 1'}]
        }
        path_obj_actual = utils.add_basic_auth(path_obj)
        path_obj_expected = {
            'tags': ['session'],
            'method': 'post',
            'path': '/com/vmware/cis/session',
            'summary': 'mock documentation',
            'responses': {'response code 1': {}, 'response code 2' : {} },
            'consumes': 'mock consumes',
            'produces': 'mock produces',
            'operationId': 'mock id',
            'security': [{'basic_auth': []}],
            'parameters': [{'mock params':'params 1'}]
        }
        self.assertEqual(path_obj_expected, path_obj_actual)
    
    def test_extract_body_parameters(self):
        # check for presence of body parameters inside params list
        # parameter 1
        field_info_mock_1 = mock.Mock()
        element_map_mock_1 = mock.Mock()
        field_info_mock_1.metadata = {'Body' : element_map_mock_1}
        #parameter 2
        field_info_mock_2 = mock.Mock()
        element_map_mock_2 = mock.Mock()
        field_info_mock_2.metadata = {'element_map_key' : element_map_mock_2}
        params = [field_info_mock_1, field_info_mock_2]
        body_params_actual, other_params_actual = utils.extract_body_parameters(params)
        body_params_expected = [field_info_mock_1]
        other_params_expected = [field_info_mock_2]
        self.assertEqual(body_params_expected, body_params_actual)
        self.assertEqual(other_params_expected, other_params_actual)
    
    def test_extract_query_parameters(self):
        # check for presence of query parameters inside params list
        # parameter 1
        field_info_mock_1 = mock.Mock()
        element_map_mock_1 = mock.Mock()
        field_info_mock_1.metadata = {'element_map_key' : element_map_mock_1}
        #parameter 2
        field_info_mock_2 = mock.Mock()
        element_map_mock_2 = mock.Mock()
        field_info_mock_2.metadata = {'Query' : element_map_mock_2}
        params = [field_info_mock_1, field_info_mock_2]
        query_params_actual, other_params_actual = utils.extract_query_parameters(params)
        query_params_expected = [field_info_mock_2]
        other_params_expected = [field_info_mock_1]
        self.assertEqual(query_params_expected, query_params_actual)
        self.assertEqual(other_params_expected, other_params_actual)
    
    def test_metamodel_to_swagger_type_converter(self):
        input_type_cases = ['date_time', 'secret', 'any_error', 'opaque',
                            'dynamic_structure', 'uri', 'id', 
                            'long', 'double', 'binary', 'notValidType']
        input_type_out_expected = [('string','date-time'), ('string', 'password'), ('string', None), 
                                   ('object', None), ('object', None), ('string', 'uri'), ('string', None), 
                                   ('integer', 'int64'), ('number', 'double'), ('string', 'binary'), 
                                   ('notvalidtype', None)]
        input_type_out_actual = []
        for val in input_type_cases:
            input_type_out_actual.append(utils.metamodel_to_swagger_type_converter(val))
        self.assertEqual(input_type_out_actual, input_type_out_expected)
    
    def test_is_type_builtin(self):
        typeset_cases          = ['binary', 'boolean', 'datetime',
                                  'double', 'dynamicstructure', 'exception', 
                                  'id', 'long', 'opaque', 'secret', 'string', 'uri']
        typeset_cases_out_expected = [True]*len(typeset_cases)
        typeset_cases_out_actual   = []
        for val in typeset_cases:
            typeset_cases_out_actual.append(utils.is_type_builtin(val))
        self.assertEqual(typeset_cases_out_actual, typeset_cases_out_expected)
    
    def test_add_query_param(self):
        #case 1: url already contains vmw-task=true query parameter
        url = '/package/mock-1/{mock}/mock?vmw-task=true'
        param = 'vmw-task=true'
        url_actual = utils.add_query_param(url,param)
        url_expected = '/package/mock-1/{mock}/mock?vmw-task=true'
        self.assertEqual(url_expected, url_actual)

        #case 2: url contains a query parameter, so append vmw-task=true using '&'
        url = '/package/mock-1/{mock}/mock?key=value'
        param = 'vmw-task=true'
        url_actual = utils.add_query_param(url,param)
        url_expected = '/package/mock-1/{mock}/mock?key=value&vmw-task=true'
        self.assertEqual(url_expected, url_actual)

        #case 3: query index not find
        url = '/package/mock-1/{mock}/mock'
        param = 'vmw-task=true'
        url_actual = utils.add_query_param(url,param)
        url_expected = '/package/mock-1/{mock}/mock?vmw-task=true'
        self.assertEqual(url_expected, url_actual)
    
    def test_create_req_body_from_params_list(self):
        # case 1: Parameters array is empty
        path_obj = {
            'parameters':[]
        }
        path_obj_expected = path_obj
        utils.create_req_body_from_params_list(path_obj)
        self.assertEqual(path_obj, path_obj_expected)

        # case 2: Parameters array contains dictionary with key as '$ref' and
        # value starting with '#/components/requestBodies' (only for put, post and patch operations)
        path_obj = {
            'parameters':[
                {'mock-param-1':{}},
                {'$ref':'#/components/requestBodies/mock-path'},
                {'mock-param-2':{}},
            ]
        }
        utils.create_req_body_from_params_list(path_obj)
        path_obj_expected = {
            'parameters': [
                {'mock-param-1': {}},
                {'mock-param-2': {}}
                ], 
                'requestBody': {'$ref': '#/components/requestBodies/mock-path'}
        }
        self.assertEqual(path_obj, path_obj_expected)

        # case 3: No dictionary with key as '$ref' inside parameters array
        path_obj = {
            'parameters':[
                {'mock-param-1':{}},
                {'mock-param-2':{}},
            ]
        }
        utils.create_req_body_from_params_list(path_obj)
        path_obj_expected = {
            'parameters':[
                {'mock-param-1':{}},
                {'mock-param-2':{}},
            ]
        }
        self.assertEqual(path_obj, path_obj_expected)


class TestPathProcessing(unittest.TestCase):

    path_process = PathProcessing()

    def test_remove_com_vmware_from_dict(self):
        '''
        case 1 (path dict processing): removing com.vmware. from every key-value pair
        which contains it and $ from every ref value of definition.
            case 1.1: remove com.vmware from value when key is either of ('$ref', 'summary', 'description')
            case 1.2: removing $ sign from ref value's, example: { "$ref" : "#/definitions/vcenter.vcha.cluster.failover$task_result" }
            case 1.3: removing attribute required when it is with '$ref'
        '''
        path_dict = {
            'com/vmware/mock/path':{
                'get': {
                    'tags': ['mock'], 
                    'summary': 'com.vmware.mock',  # 1.1:  example 1
                    'parameters': [
                        {
                            "in" : "path",
                            "description" : "com.vmware.somemockparam description" # 1.1: example 2
                        },
                        {
                            "$ref": '#/parameters/com.vmware.somemockparam' # 1.1 : example 3
                        }
                    ], 
                    'responses': {
                        'mock 200': {
                            'description': 'description about com.vmware.mock_response',
                            'schema': {
                                '$ref': '#/definitions/com.vmware.mock_response$result', # 1.2
                                'required': False # 1.3
                            }
                        }
                    },
                    'operationId': 'get'
                }
            }
        }
        path_dict_expected = {
            'com/vmware/mock/path': {
                'get': {
                    'tags': ['mock'], 
                    'summary': 'mock', 
                    'parameters': [
                        {
                            'in': 'path', 
                            'description': 'somemockparam description'
                        }, 
                        {
                            '$ref': '#/parameters/somemockparam'
                        }
                    ],
                    'responses': {
                        'mock 200': {
                            'description': 'description about mock_response', 
                            'schema': {
                                '$ref': '#/definitions/mock_response_result'
                            }
                        }
                    },
                    'operationId': 'get'
                }
            }
        }
        self.path_process.remove_com_vmware_from_dict(path_dict)   
        self.assertEqual(path_dict, path_dict_expected)

        '''
        case 2 (type dict processing)
            case 2.1 : remove com.vmware and replace '$' with '_' from key's
            case 2.2 : removing attribute required when it is with '$ref'
        '''
        type_dict = { 
            'com.vmware.mock.mock_check$list' : { # 2.1 : example 1
                'type': 'object', 
                'properties': {
                    'value': {
                        'description': ' value desc.', 
                        'type': 'array', 
                        'items': {
                            '$ref': '#/definitions/com.vmware.mock_check_item', # 2.1 : example 2
                            'required': True # 2.2
                        }
                    },
                    'data': {
                        'description': ' data desc ', 
                        'type': 'object'
                    },
                    'required': ['value']
                }
            }
        }
        type_dict_expected = {
            'mock.mock_check_list': {
                'type': 'object', 
                'properties': {
                    'value': {
                        'description': 
                        ' value desc.', 
                        'type': 'array', 
                        'items': {
                            '$ref': '#/definitions/mock_check_item'
                        }
                    }, 
                    'data': {
                        'description': ' data desc ', 
                        'type': 'object'
                    }, 
                    'required': ['value']
                }
            }
        }
        self.path_process.remove_com_vmware_from_dict(type_dict)
        self.assertEqual(type_dict, type_dict_expected)

    def test_create_camelized_op_id(self):
        # Note: create_unique_op_ids(path_dict) test cases are handled in test cases provided for create_camelized_op_id
        # case 1: without query parameter: removes com/vmware/ and replaces '/' & '-' with '_' 
        # also converts the first letter of all the words except the first one from lower to upper before concatenating to form unique op id
        path = "com/vmware/mock-path"
        http_method = "post"
        operations_dict = {
            'operationId' : 'post'
        }
        op_id_expected = 'postMockPath'
        op_id_actual = self.path_process.create_camelized_op_id(path, http_method, operations_dict)
        self.assertEqual(op_id_actual, op_id_expected)

        # case 2 : similar to case 1 with added query param to path
        path = "com/vmware/mock-path?action=value"
        http_method = "post"
        operations_dict = {
            'operationId' : 'mock-operation-id'
        }
        op_id_expected = 'mockOperationIdMockPath'
        op_id_actual = self.path_process.create_camelized_op_id(path, http_method, operations_dict)
        self.assertEqual(op_id_actual, op_id_expected)

        # case 3 : similar to case 1 with path variable
        path = "com/vmware/mock-path/{mock}/test"
        http_method = "post"
        operations_dict = {
            'operationId' : 'post'
        }
        op_id_expected = 'postMockPathTest'
        op_id_actual = self.path_process.create_camelized_op_id(path, http_method, operations_dict)
        self.assertEqual(op_id_actual, op_id_expected)

    def test_create_unique_op_ids(self):
        # update path dictionary with unique operation id
        path_dict = {
            'com/vmware/mock-path':{
                'post': {
                    'operationId' : 'post'
                }
            }
        }
        self.path_process.create_unique_op_ids(path_dict)
        path_dict_expected = {
            'com/vmware/mock-path':{
                'post': {
                    'operationId' : 'postMockPath'
                }
            }
        }
        self.assertEqual(path_dict, path_dict_expected)

    def test_merge_dictionaries(self):
        # generic test for updating a dictionary by adding keys from second dict
        dict_one = {
            'key 1' : 'value 1',
            'key 2' : 'value 2'
        }
        dict_two = {
            'key 3' : 'value 3',
            'key 4' : 'value 4'
        }
        dict_expected = {
            'key 1' : 'value 1',
            'key 2' : 'value 2',
            'key 3' : 'value 3',
            'key 4' : 'value 4'
        }
        dict_actual = self.path_process.merge_dictionaries(dict_one, dict_two)
        self.assertEqual(dict_expected, dict_actual)
        
class TestUrlProcessing(unittest.TestCase):

    url_process = UrlProcessing()

    def test_find_url(self):
        # case 1: if only one element is in the list return it
        list_of_links = [{'method': 'POST', 'href':'https://vcip/rest/com/vmware/mock?~action=value'}]
        expected_return = ('https://vcip/rest/com/vmware/mock?~action=value','POST')
        actual_return = self.url_process.find_url(list_of_links)
        self.assertEqual(expected_return, actual_return)    

        # case 2: if multiple links are provided
        # case 2.1 : return a link which does not contain "~action"
        list_of_links = [
            {'method': 'POST', 'href':'https://vcip/rest/com/vmware/mock?~action=value'},
            {'method': 'POST', 'href':'https://vcip/rest/com/vmware/mock-action-value'}
        ]
        expected_return = ('https://vcip/rest/com/vmware/mock-action-value','POST')
        actual_return = self.url_process.find_url(list_of_links)
        self.assertEqual(expected_return, actual_return)

        # case 2.2 : all links have ~action in them then check if any of them has id: and return it.
        list_of_links = [
            {'method': 'POST', 'href':'https://vcip/rest/com/vmware/mock?~action=value'},
            {'method': 'POST', 'href':'https://vcip/rest/com/vmware/mock/id:{mock_id}?~action=value'}
        ]
        expected_return = ('https://vcip/rest/com/vmware/mock/id:{mock_id}?~action=value','POST')
        actual_return = self.url_process.find_url(list_of_links)
        self.assertEqual(expected_return, actual_return)

        # case 2.3 : all links have ~action in them and none of them have id:, pick any by default first one.
        list_of_links = [
            {'method': 'POST', 'href':'https://vcip/rest/com/vmware/mock?~action=value1'},
            {'method': 'POST', 'href':'https://vcip/rest/com/vmware/mock?~action=value2'}
        ]
        expected_return = ('https://vcip/rest/com/vmware/mock?~action=value1','POST')
        actual_return = self.url_process.find_url(list_of_links)
        self.assertEqual(expected_return, actual_return)

    def test_convert_path_list_to_path_map(self):
        # combine the path objects having same path but different methods inside them into a path dictionary
        path_object_1 = {
        'path': '/package/mock',
        'method': 'get'
        }
        path_object_2 = {
            'path': '/package/mock',
            'method': 'post'
        }
        path_object_3 = {
            'path': 'package/mock/mock',
            'method': 'patch'
        }
        path_list = [path_object_1, path_object_2, path_object_3]
        path_dict_actual = self.url_process.convert_path_list_to_path_map(path_list)
        path_dict_expected = {
            '/package/mock': { 
                               'get': path_object_1, 
                               'post': path_object_2 
                             },       
            'package/mock/mock': { 
                                'patch': path_object_3
            }
        }
        self.assertEqual(path_dict_expected, path_dict_actual)
    
    def test_cleanup(self):
        # case 1: cleanup for [path dict]
        # delete path and method inside path_dict[method] because key is the path and value of path_dict's key is method, hence remove the redundant data.
        path_dict = {
            'mock_path':{
                'mock_method_1':{
                    'mock_attr': 'value',
                    'method': 'mock_method_1', 
                    'path': 'mock_path'
                    },
                'mock_method_2':{
                    'mock_attr': 'value',
                    'method': 'mock_method_2', 
                    'path': 'mock_path'
                    }  
                }
            }
        type_dict = {}
        path_dict_expected = {
            'mock_path':{
                'mock_method_1':{
                    'mock_attr': 'value',
                    },
                'mock_method_2':{
                    'mock_attr': 'value',
                    }  
                }
            }
        self.url_process.cleanup(path_dict, type_dict)
        self.assertEqual(path_dict, path_dict_expected)

        # case 2: cleanup for [type dict]
        # delete attribute named 'required' present in any property of any model's structure type 
        type_dict = {
            'mock.type':{
                'properties':{
                    'mock property 1':{
                        'required': True
                    },
                    'mock property 2':{
                    }
                }
            }
        }
        path_dict = {}
        type_dict_expected = {
            'mock.type':{
                'properties':{
                    'mock property 1':{
                    },
                    'mock property 2':{ 
                    }
                }
            }
        }
        self.url_process.cleanup(path_dict, type_dict)
        self.assertEqual(type_dict, type_dict_expected)

class TestTypeHandlerCommon(unittest.TestCase):

    type_handler = TypeHandlerCommon()

    def test_visit_builtin(self):
        # create property object with builtin type as 'Boolean'
        builtin_type = 'BOOLEAN'
        new_prop     = {}
        expected     = {'type':'boolean'}
        self.type_handler.visit_builtin(builtin_type, new_prop)
        self.assertEqual(new_prop, expected)

        # create property object with builtin type as 'date_time'
        builtin_type = 'date_time'
        new_prop     = {}
        expected     = {'type':'string', 'format':'date-time'}
        self.type_handler.visit_builtin(builtin_type, new_prop)
        self.assertEqual(new_prop, expected)

        # create property object with builtin type as 'dynamic_structure'
        builtin_type = 'dynamic_structure'
        new_prop     = {}
        expected     = {'type':'object'}
        self.type_handler.visit_builtin(builtin_type, new_prop)
        self.assertEqual(new_prop, expected)

        # create property object with builtin type as 'long'
        builtin_type = 'long'
        new_prop     = {'type':'array'}
        expected     = {'items': {'format': 'int64', 'type': 'integer'}, 'type': 'array'}
        self.type_handler.visit_builtin(builtin_type, new_prop)
        self.assertEqual(new_prop, expected)
    
    def test_get_enum_info(self):
        # case 1: type_name is present in enum dict
        # case 1.1: metadata of enum info object is not filtered
        enum_info_mock = mock.Mock()
        enum_info_mock.metadata = {'TechPreview': {} }
        enum_dict = {
            'com.vmware.package.mock': enum_info_mock
        }
        '''
        The structure of enum dict is as follows:
        enum_dict = {
            'com.vmware.package.mock' : EnumerationInfo(metadata = {
            'TechPreview : {}
            })
        }
        '''
        enum_info_expected = enum_info_mock
        enum_info_actual = self.type_handler.get_enum_info('com.vmware.package.mock', enum_dict, True)
        self.assertEqual(enum_info_expected, enum_info_actual)
        
        # case 1.2: metadata of enum info object is filtered
        enum_info_mock.metadata = {'Changing': {} }
        enum_info_actual = self.type_handler.get_enum_info('com.vmware.package.mock', enum_dict, True)
        self.assertEqual(enum_info_actual, None)

        # case 2: type_name is not present in enum_dict
        enum_info_actual = self.type_handler.get_enum_info('com.vmware.package.mock-1', enum_dict, True)
        self.assertEqual(enum_info_actual, None)
        
    def test_process_enum_info(self):
        # write the unfiltered metadata of enum info object's values in type dictionary
        enum_info_mock = mock.Mock()
        enum_value_info_mock_1 = mock.Mock()
        enum_value_info_mock_1.metadata = {'TechPreview': {} }
        enum_value_info_mock_1.value = 'enumMockValue-1'
        enum_value_info_mock_2 = mock.Mock()
        enum_value_info_mock_2.metadata = {'Changing': {} }
        enum_value_info_mock_2.value = 'enumMockValue-2'
        enum_info_mock.documentation = 'SomeMockDescription'
        enum_info_mock.values = [enum_value_info_mock_1, enum_value_info_mock_2]
        '''
        The structure of enum dict created above is as follows:
        enum_dict = {
            'com.vmware.package.mock': EnumerationInfo( values = [
                EnumerationValueInfo( value = enumMockValue-1, metadata = {'TechPreview': {} }),
                EnumerationValueInfo( value = enumMockValue-1, metadata = {'Changing': {} })
            ])
        }
        '''
        type_dict = {}
        type_dict_expected = {
            'com.vmware.package.mock': {
                'type': 'string',
                'description': 'SomeMockDescription',
                'enum': ['enumMockValue-1']
            }
        }
        self.type_handler.process_enum_info('com.vmware.package.mock', enum_info_mock, type_dict, True)
        self.assertEqual(type_dict_expected, type_dict)
    
    def test_get_structure_info(self):
        # case 1: type_name is present in structure dict
        # case 1.1: metadata of structure info object is not filtered
        structure_info_mock = mock.Mock()
        field_info_mock_1 = mock.Mock()
        field_info_mock_1.metadata = {'TechPreview': {} }
        field_info_mock_2 = mock.Mock()
        field_info_mock_2.metadata = {'Changing': {} }
        structure_info_mock.metadata = {'TechPreview' : {} }
        structure_dict = {
            'com.vmware.package.mock': structure_info_mock
        }
        structure_info_mock.fields = [field_info_mock_1, field_info_mock_2]
        '''
        The above structure dict definition is as follows:
        structure_dict = {
            'com.vmware.package.mock': StructureInfo( metadata = 'TechPreview': {}
            fields = [ 
                       FieldInfo( metadata = { 'TechPreview': {} }),
                       FieldInfo( metadata = { 'Changing': {} })
                     ] 
            )
        }
        '''
        structure_info_actual = self.type_handler.get_structure_info('com.vmware.package.mock', structure_dict, True)
        structure_info_mock.fields = [field_info_mock_1] # modification after processing field info objects 
        self.assertEqual(structure_info_mock, structure_info_actual)

        # case 1.2: metadata of structure info object is filtered
        structure_info_mock.metadata = {'Changing' : {} }
        structure_info_actual = self.type_handler.get_structure_info('com.vmware.package.mock', structure_dict, True)
        self.assertEqual(structure_info_actual, None)

        # case 2: type_name is not present in structure dict
        structure_info_actual = self.type_handler.get_structure_info('com.vmware.package.mock-1', structure_dict, True)
        self.assertEqual(structure_info_actual, None)
    
    def test_process_structure_info(self):
        # case 1: processing for field info type as Builtin
        field_info_mock = mock.Mock()
        field_info_type = mock.Mock()
        field_info_type.category = 'BUILTIN'
        field_info_type.builtin_type = 'date-time'
        field_info_mock.type = field_info_type
        field_info_mock.documentation = 'fieldInfoMockDescription'
        field_info_mock.name = 'fieldInfoMockName'
        structure_info_mock = mock.Mock()
        structure_info_mock.fields = [field_info_mock]
        structure_dict = {
            'com.vmware.package.mock': structure_info_mock
        }
        enum_dict = {}
        type_dict = {}
        self.type_handler.process_structure_info('com.vmware.package.mock', structure_info_mock, 
                                             type_dict, structure_dict, enum_dict, '#/definitions/', True)
        type_dict_expected = {
            'com.vmware.package.mock': {
                'type': 'object',
                'properties': {
                    'fieldInfoMockName': {
                        'description': 'fieldInfoMockDescription',
                        'type': 'date-time'
                    }
                },
                'required': ['fieldInfoMockName']
            }
        }
        self.assertEqual(type_dict_expected, type_dict)

        # case 2: processing for field info type as user-defined
        # handled inside test cases for visit_user_defined() function

        # case 3: processing for field info type as generic
        # handled inside test cases for visit_generic() function
   
    def test_check_type(self):
        # case 1: Populate type dictionary for resource type as 'com.vmware.vapi.structure'
        field_info_mock = mock.Mock()
        field_info_type = mock.Mock()
        field_info_type.category = 'BUILTIN'
        field_info_type.builtin_type = 'date-time'
        field_info_mock.type = field_info_type
        field_info_mock.documentation = 'fieldInfoMockDescription'
        field_info_mock.name = 'fieldInfoMockName'
        structure_info_mock = mock.Mock()
        structure_info_mock.fields = [field_info_mock]
        structure_dict = {
            'com.vmware.package.mock': structure_info_mock
        }
        enum_dict = {}
        type_dict = {}
        self.type_handler.check_type('com.vmware.vapi.structure', 'com.vmware.package.mock', type_dict, structure_dict, enum_dict, '#/definitions/', False)
        type_dict_expected = {
            'com.vmware.package.mock': {
                'type': 'object',
                'properties': {
                    'fieldInfoMockName': {
                        'description': 'fieldInfoMockDescription',
                        'type': 'date-time'
                    }
                },
                'required': ['fieldInfoMockName']
            }
        }
        self.assertEqual(type_dict_expected, type_dict) 

        # case 2: Populate type dictionary for enumeration type as 'com.vmware.vapi.enumeration'
        enum_info_mock = mock.Mock()
        enum_value_info_mock_1 = mock.Mock()
        enum_value_info_mock_1.metadata = {'TechPreview': {} }
        enum_value_info_mock_1.value = 'enumMockValue-1'
        enum_value_info_mock_2 = mock.Mock()
        enum_value_info_mock_2.metadata = {'Changing': {} }
        enum_value_info_mock_2.value = 'enumMockValue-2'
        enum_info_mock.documentation = 'SomeMockDescription'
        enum_info_mock.values = [enum_value_info_mock_1, enum_value_info_mock_2]
        enum_dict = {
            'com.vmware.package.mock': enum_info_mock
        }
        structure_dict = {}
        type_dict = {}
        self.type_handler.check_type('com.vmware.vapi.enum-mock', 'com.vmware.package.mock', type_dict, structure_dict, enum_dict, '#/definitions/', False)
        type_dict_expected = {
            'com.vmware.package.mock': {
                'type': 'string',
                'description': 'SomeMockDescription',
                'enum': ['enumMockValue-1', 'enumMockValue-2']
            }
        }
        self.assertEqual(type_dict_expected, type_dict)
   
    def test_visit_user_defined(self):
        # case 1: resource id of user defined type is none
        user_defined_type_mock = mock.Mock()
        user_defined_type_mock.resource_id = None
        new_prop = {}
        self.type_handler.visit_user_defined(user_defined_type_mock, new_prop, {}, {}, {}, '#/definitions/', False)
        new_prop_expected = {}
        self.assertEqual(new_prop_expected, new_prop)

        # case 2: check for user defined type as structure
        user_defined_type_mock.resource_type = 'com.vmware.vapi.structure'
        user_defined_type_mock.resource_id = 'com.vmware.package.mock'
        field_info_mock = mock.Mock()
        field_info_type = mock.Mock()
        field_info_type.category = 'BUILTIN'
        field_info_type.builtin_type = 'date-time'
        field_info_mock.type = field_info_type
        field_info_mock.user_defined_type = user_defined_type_mock
        field_info_mock.documentation = 'fieldInfoMockDescription'
        field_info_mock.name = 'fieldInfoMockName'
        structure_info_mock = mock.Mock()
        structure_info_mock.fields = [field_info_mock]
        structure_dict = {
            'com.vmware.package.mock': structure_info_mock
        }
        new_prop = {'type': 'array'}
        self.type_handler.visit_user_defined(user_defined_type_mock, new_prop, {}, structure_dict, {}, '#/definitions/', False)
        new_prop_expected = {'type': 'array', 'items': {'$ref': '#/definitions/com.vmware.package.mock'}}
        self.assertEqual(new_prop_expected, new_prop)

        # case 3: check for user defined type as enumerration
        # handled in test cases for check_type() function

if __name__ == '__main__':
    unittest.main()