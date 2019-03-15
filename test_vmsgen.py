import vmsgen
import unittest
from unittest import mock as mock

class TestVmsGen(unittest.TestCase):

    def test_tags_from_service_name(self):

        # case 1: tags generation from short name
        expected = ['']
        vmsgen.TAG_SEPARATOR = ''
        actual = vmsgen.tags_from_service_name('three.levels.deep')
        self.assertEqual(expected, actual)

        # case 2: test tags generation from proper name
        expected = ['levels_deep']
        vmsgen.TAG_SEPARATOR = '_'
        actual = vmsgen.tags_from_service_name('more.than.three.levels.deep')
        self.assertEqual(expected, actual)

    def test_get_input_params(self):

        # case 1.1: SSL is secure
        test_args = ['vmsgen', '-vc', 'v_url']
        ssl_verify_expected = True
        with mock.patch('sys.argv', test_args):
            _, _, _, ssl_verify_actual = vmsgen.get_input_params()
        self.assertEqual(ssl_verify_expected, ssl_verify_actual)

        # case 1.2: SSL is insecure
        test_args = ['vmsgen', '-vc', 'v_url', '-k']
        ssl_verify_expected = False
        with mock.patch('sys.argv', test_args):
            _, _, _, ssl_verify_actual = vmsgen.get_input_params()
        self.assertEqual(ssl_verify_expected, ssl_verify_actual)

        # case 2.1: tag separator option (default)
        test_args = ['vmsgen', '-vc', 'v_url', '-k']
        tag_separator_expected = '/'
        with mock.patch('sys.argv', test_args):
            vmsgen.get_input_params()
        self.assertEqual(tag_separator_expected, vmsgen.TAG_SEPARATOR)

        # case 2.2: tag separator option
        expected = '_'
        test_args = ['vmsgen', '-vc', 'v_url', '-s', expected]
        with mock.patch('sys.argv', test_args):
            vmsgen.get_input_params()
        self.assertEqual(expected, vmsgen.TAG_SEPARATOR)

        # case 3.1: operation id option is FALSE
        test_args = ['vmsgen', '-vc', 'v_url', '-k']
        generate_op_id_expected = False
        with mock.patch('sys.argv', test_args):
            vmsgen.get_input_params()
        self.assertEqual(generate_op_id_expected, vmsgen.GENERATE_UNIQUE_OP_IDS)

        # case 3.1: operation id option is TRUE
        generate_op_id_expected = True
        test_args = ['vmsgen', '-vc', 'v_url', '-k', '-uo']
        with mock.patch('sys.argv', test_args):
            vmsgen.get_input_params()
        self.assertEqual(generate_op_id_expected, vmsgen.GENERATE_UNIQUE_OP_IDS)

    def test_post_process_path(self):
        '''
            Test cases to check if post process path which adds vmware-use-header-authn as a nessecary header params
        '''
        # case 1: case where hardcoded header should be added
        path_obj = {'path':'/com/vmware/cis/session', 'method':'post'}
        header_parameter = {'in': 'header', 'required': True, 'type': 'string',
                            'name': 'vmware-use-header-authn',
                            'description': 'Custom header to protect against CSRF attacks in browser based clients'}
        path_obj_expected  = {'path':'/com/vmware/cis/session', 'method':'post', 'parameters':[header_parameter]}
        vmsgen.post_process_path(path_obj)
        self.assertEqual(path_obj_expected, path_obj)

        # case 2.1: case where hardcoded header should be shouldn't be added based on path
        path_obj = {'path':'mock/path', 'method':'post'}
        path_obj_expected  = {'path':'mock/path', 'method':'post'}
        vmsgen.post_process_path(path_obj)
        self.assertEqual(path_obj_expected, path_obj)

        # case 2.1: case where hardcoded header should be shouldn't be added based on method
        path_obj = {'path':'/com/vmware/cis/session', 'method':'get'}
        path_obj_expected  = {'path':'/com/vmware/cis/session', 'method':'get'}
        vmsgen.post_process_path(path_obj)
        self.assertEqual(path_obj_expected, path_obj)

    def test_get_response_object_name(self):
        '''
           test case for response type name to be used based on method is get or not  
        '''
        # case 1:
        operation_id = 'get'
        service_id = 'tag'
        type_name = 'tag'
        type_name_expected = vmsgen.get_response_object_name(service_id, operation_id)
        self.assertEqual(type_name, type_name_expected)

        # case 2:
        operation_id = 'post'
        service_id = 'tag'
        type_name = 'tag.post'
        type_name_expected = vmsgen.get_response_object_name(service_id, operation_id)
        self.assertEqual(type_name, type_name_expected)

    def test_is_type_builtin(self):
        '''
        '''
        typeset_cases          = ['binary', 'boolean', 'datetime', 'double', 'dynamicstructure', 'exception', 'id', 'long', 'opaque', 'secret', 'string', 'uri']
        
        typeset_cases_out_expected = [True]*len(typeset_cases)
        typeset_cases_out_actual   = []
        
        for val in typeset_cases:
            typeset_cases_out_actual.append(vmsgen.is_type_builtin(val))

        self.assertEqual(typeset_cases_out_actual, typeset_cases_out_expected)
        
    def test_metamodel_to_swagger_type_converter(self):

        input_type_cases        = ['date_time', 'secret', 'any_error', 'dynamic_structure', 'uri', 'id', 'long', 'double', 'binary', 'notValidType']
        
        input_type_out_expected = [('string','date-time'), ('string', 'password'), ('string', None), ('object', None), ('string', 'uri'), ('string', None), ('integer', 'int64'), ('number', 'double'), ('string', 'binary'), ('notvalidtype', None)]
        input_type_out_actual   = []

        for val in input_type_cases:
            input_type_out_actual.append(vmsgen.metamodel_to_swagger_type_converter(val))

        self.assertEqual(input_type_out_actual, input_type_out_expected)

    def test_visit_builtin(self):

        builtin_type = 'BOOLEAN'
        new_prop     = {}
        expected     = {'type':'boolean'}
        vmsgen.visit_builtin(builtin_type, new_prop)
        self.assertEqual(new_prop, expected)

        builtin_type = 'date_time'
        new_prop     = {}
        expected     = {'type':'string', 'format':'date-time'}
        vmsgen.visit_builtin(builtin_type, new_prop)
        self.assertEqual(new_prop, expected)

        builtin_type = 'dynamic_structure'
        new_prop     = {}
        expected     = {'type':'object'}
        vmsgen.visit_builtin(builtin_type, new_prop)
        self.assertEqual(new_prop, expected)

        builtin_type = 'long'
        new_prop     = {'type':'array'}
        expected     = {'items': {'format': 'int64', 'type': 'integer'}, 'type': 'array'}
        vmsgen.visit_builtin(builtin_type, new_prop)
        self.assertEqual(new_prop, expected)



    def test_build_path(self):

        # function def : build_path(service_name, method, path, documentation, parameters, operation_id, responses, consumes, produces)

        # case 1: generic mock example
        expected = {
            'tags': ['mock_tag'], 
            'method': 'get', 
            'path': '/com/vmware/mock_package/mock_tag', 
            'summary': 'mock documentation', 
            'responses': 'mock responses', 
            'consumes': 'mock consumes', 
            'produces': 'mock produces', 
            'operationId': 'mock id', 
            'parameters': [{'mock params':'params 1'}]
        }
        actual = vmsgen.build_path('com.vmware.mock_package.mock_tag', 'get', '/com/vmware/mock_package/mock_tag', 'mock documentation', [{'mock params':'params 1'}], 'mock id', 'mock responses','mock consumes', 'mock produces')
        self.assertEqual(actual, expected)

        # case 2 related specifically to '/com/vmware/cis/session'  
        # case 2.1: case where hardcoded header should be added
        expected = {
            'tags': ['session'], 
            'method': 'post', 
            'path': '/com/vmware/cis/session', 
            'summary': 'mock documentation', 
            'responses': 'mock responses', 
            'consumes': 'mock consumes', 
            'produces': 'mock produces', 
            'operationId': 'mock id', 
            'parameters': [
                {
                    'in': 'header', 
                    'required': True, 
                    'type': 'string', 
                    'name': 'vmware-use-header-authn', 
                    'description': 'Custom header to protect against CSRF attacks in browser based clients'
                }
            ]
        }
        actual = vmsgen.build_path('com.vmware.cis.session', 'post', '/com/vmware/cis/session', 'mock documentation', None, 'mock id', 'mock responses','mock consumes', 'mock produces')
        self.assertEqual(actual, expected)
        
        # case 2.2: case where hardcoded header shouldn't be added shown here only based on method but same can be done for path
        expected = {
            'tags': ['session'], 
            'method': 'get', 
            'path': '/com/vmware/cis/session', 
            'summary': 'mock documentation', 
            'responses': 'mock responses', 
            'consumes': 'mock consumes', 
            'produces': 'mock produces', 
            'operationId': 'mock id', 
            'parameters': [{'mock params':'params 1'}]
        }
        actual = vmsgen.build_path('com.vmware.cis.session', 'get', '/com/vmware/cis/session', 'mock documentation', [{'mock params':'params 1'}], 'mock id', 'mock responses','mock consumes', 'mock produces')
        self.assertEqual(actual, expected)


    def test_cleanup(self):

        # case 1: [path dict] -> delete path and method mentioned inside path_dict value because key is the path and value of path_dict's key is method, hence remove the redundant data.
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

        type_dict = {}

        vmsgen.cleanup(path_dict, type_dict)
        self.assertEqual(path_dict, path_dict_expected)

        # case 2: [type dict] -> delete attribute named 'required' present in any property of any model's structure type 
        path_dict = {}
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
        vmsgen.cleanup(path_dict, type_dict)
        self.assertEqual(type_dict, type_dict_expected)

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
        vmsgen.remove_query_params(path_dict)
        self.assertEqual(path_dict, path_dict_expected)


        # case 2: Partial Duplicate, adding the Operations of the new duplicate path to that of the existing path based on method type
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
                            'type': 'string', 
                            'enum': ['mock_action']
                        }
                    ]
                }, 
                'get': {
                    'parameters' : []
                }
            }
        }
        vmsgen.remove_query_params(path_dict)
        self.assertEqual(path_dict, path_dict_expected)

        # case 2.2: both of them has query parameter
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
                'post': {
                    'parameters': [{'name': 'action',  'in': 'query', 'description': 'action=mock_action_1', 'required': True, 'type': 'string', 'enum': ['mock_action_1']}]
                }, 
                'get': {
                    'parameters': [{'name': 'action',  'in': 'query', 'description': 'action=mock_action_2', 'required': True, 'type': 'string', 'enum': ['mock_action_2']}]
                }
            }
        }
        vmsgen.remove_query_params(path_dict)
        self.assertEqual(path_dict, path_dict_expected)

        # case 3: QueryParameters are fixed
        # case 3.1 : method types are different
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
                    'parameters': [{'name': 'action', 'in': 'query', 'description': 'action=mock_action_2', 'required': True, 'type': 'string', 'enum': ['mock_action_2']}]
                }, 
                'post': {
                    'parameters': [{'name': 'action', 'in': 'query', 'description': 'action=mock_action_1', 'required': True, 'type': 'string', 'enum': ['mock_action_1']}]
                }
            }
        }

        vmsgen.remove_query_params(path_dict)
        self.assertEqual(path_dict, path_dict_expected)

        # case 3.2 : method types are same
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
            'mock/path1': {
                'post': {
                    'parameters': [{'name': 'action', 'in': 'query', 'description': 'action=mock_action_1', 'required': True, 'type': 'string', 'enum': ['mock_action_1']}]
                }
            },
            'mock/path1?action=mock_action_2': {
                'post': {
                    'parameters': []
                }
            }
        }
        vmsgen.remove_query_params(path_dict)
        self.assertEqual(path_dict, path_dict_expected)

if __name__ == '__main__':
    unittest.main()
