import os
import re
import collections
from lib import utils

def process_output(path_dict, type_dict, output_dir, output_filename, gen_unique_op_id):
    description_map = utils.load_description()
    remove_com_vmware_from_dict(path_dict)
    if gen_unique_op_id:
        create_unique_op_ids(path_dict)
    remove_query_params(path_dict)
    remove_com_vmware_from_dict(type_dict)
    swagger_template = {'swagger': '2.0',
                        'info': {'description': description_map.get(output_filename, ''),
                                 'title': output_filename,
                                 'termsOfService': 'http://swagger.io/terms/',
                                 'version': '2.0.0'}, 
                        'host': '<vcenter>',
                        'securityDefinitions': {'basic_auth': {'type': 'basic'}},
                        'basePath': '/rest', 'tags': [],
                        'schemes': ['https', 'http'],
                        'paths': collections.OrderedDict(sorted(path_dict.items())),
                        'definitions': collections.OrderedDict(sorted(type_dict.items()))}
    
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    utils.write_json_data_to_file(output_dir + os.path.sep + '/rest' + "_" + output_filename + '.json', swagger_template)

def remove_com_vmware_from_dict(swagger_obj, depth=0, keys_list=[]):
    """
    The method
    1. removes 'com.vmware.' from model names
    2. replaces $ with _ from the model names

    This is done on both definitions and path
    'definitions' : where models are defined and may be referenced.
    'path' : where models are referenced.
    :param swagger_obj: should be path of definitions dictionary
    :param depth: depth of the dictionary. Defaults to 0
    :param keys_list: List of updated model names
    :return:
    """
    if isinstance(swagger_obj, dict):
        if '$ref' in swagger_obj and 'required' in swagger_obj:
            del swagger_obj['required']
        for key, item in swagger_obj.items():
            if isinstance(item, str):
                if key in ('$ref', 'summary', 'description'):
                    item = item.replace('com.vmware.', '')
                    if key == '$ref':
                        item = item.replace('$', '_')
                    swagger_obj[key] = item
            elif isinstance(item, list):
                for itm in item:
                    remove_com_vmware_from_dict(itm, depth+1, keys_list)
            elif isinstance(item, dict):
                if depth == 0 and isinstance(key, str) and (key.startswith('com.vmware.') or '$' in key):
                    keys_list.append(key)
                remove_com_vmware_from_dict(item, depth+1, keys_list)
    elif isinstance(swagger_obj, list):
        for itm in swagger_obj:
            remove_com_vmware_from_dict(itm, depth+1)
    if depth == 0 and len(keys_list) > 0:
        while keys_list:
            old_key = keys_list.pop()
            new_key = old_key.replace('com.vmware.', '')
            new_key = new_key.replace('$', '_')
            try:
                swagger_obj[new_key] = swagger_obj.pop(old_key)
            except KeyError:
                print('Could not find the Swagger Element :  {}'.format(old_key))


def create_camelized_op_id(path, http_method, operations_dict):
    """
    Creates camelized operation id.
    Takes the path, http_method and operation dictionary as input parameter:
    1. Iterates through all the operation array to return the current operation id
    2. Appends path to the existing operation id and
     replaces '/' and '-' with '_' and removes 'com_vmware_'
    3. Splits the string by '_'
    4. Converts the first letter of all the words except the first one from lower to upper
    5. Joins all the words together and returns the new camelcase string

    e.g
        parameter : abc_def_ghi
        return    : AbcDefGhi
    :param path:
    :param http_method:
    :param operations_dict:
    :return: new_op_id
    """
    curr_op_id = operations_dict['operationId']
    raw_op_id = curr_op_id.replace('-', '_')
    new_op_id = raw_op_id
    if '_' in raw_op_id:
        raw_op_id_iter = iter(raw_op_id.split('_'))
        new_op_id = next(raw_op_id_iter)
        for new_op_id_element in raw_op_id_iter:
            new_op_id += new_op_id_element.title()
    ''' 
        Removes query parameters form the path. 
        Only path elements are used in operation ids
    '''
    paths_array = re.split('\?', path)
    path = paths_array[0]
    path_elements = path.replace('-', '_').split('/')
    path_elements_iter = iter(path_elements)
    for path_element in path_elements_iter:
        if '{' in path_element:
            continue
        if 'com' == path_element or 'vmware' == path_element:
            continue
        if path_element.lower() == raw_op_id.lower():
            continue
        if '_' in path_element:
            sub_path_iter = iter(path_element.split('_'))
            for sub_path_element in sub_path_iter:
                new_op_id += sub_path_element.title()
        else:
            new_op_id += path_element.title()
    return new_op_id


def create_unique_op_ids(path_dict):
    """
    Creates unique operation ids
    Takes the path dictionary as input parameter:
    1. Iterates through all the http_operation array
    2. For every operation gets the current operation id
    3. Calls method to get the camelized operation id
    4. Checks for uniqueness
    5. Updates the path dictionary with the unique operation id
    
    :param path_dict:
    """
    op_id_list = ['get', 'set', 'list', 'add', 'run', 'start', 'stop',
                  'restart', 'reset', 'cancel', 'create', 'update', 'delete']
    for path, http_operation in path_dict.items():
        for http_method, operation_dict in http_operation.items():
            op_id_val = create_camelized_op_id(path, http_method, operation_dict)
            if op_id_val not in op_id_list:
                operation_dict['operationId'] = op_id_val
                op_id_list.append(op_id_val)

def remove_query_params(path_dict):
    """
    Swagger/Open API specification prohibits appending query parameter to the request mapping path.

    Duplicate paths in Open API :
        Since request mapping paths are keys in the Open Api JSON, there is no scope of duplicate request mapping paths

    Partial Duplicates in Open API: APIs which have same request mapping paths but different HTTP Operations.

    Such Operations can be merged together under one path
        eg: Consider these two paths
            /A/B/C : [POST]
            /A/B/C : [PUT]
        On merging these, the new path would look like:
        /A/B/C : [POST, PUT]

    Absolute Duplicates in Open API: APIs which have same request mapping path and HTTP Operation(s)
        eg: Consider two paths
            /A/B/C : [POST, PUT]
            /A/B/C : [PUT]
    Such paths can not co-exist in the same Open API definition.

    This method attempts to move query parameters from request mapping url to parameter section.

    There are 4 possibilities which may arise on removing the query parameter from request mapping path:

     1. Absolute Duplicate
        The combination of path and the HTTP Operation Type(s)are same to that of an existing path:
        Handling Such APIs is Out of Scope of this method. Such APIs will appear in the Open API definition unchanged.
        Example :
                /com/vmware/cis/session?~action=get : [POST]
                /com/vmware/cis/session : [POST, DELETE]
    2. Partial Duplicate:
        The Paths are same but the HTTP operations are Unique:
        Handling Such APIs involves adding the Operations of the new duplicate path to that of the existing path
        Example :
                /cis/tasks/{task}?action=cancel : [POST]
                /cis/tasks/{task} : [GET]
    3. New Unique Path:
        The new path is not a duplicate of any path in the current Open API definition.
        The Path is changed to new path by trimming off the path post '?'

    4. The duplicate paths are formed when two paths with QueryParameters are fixed
        All the scenarios under 1, 2 and 3 are possible.
        Example :
                /com/vmware/cis/tagging/tag-association/id:{tag_id}?~action=detach-tag-from-multiple-objects
                /com/vmware/cis/tagging/tag-association/id:{tag_id}?~action=list-attached-objects
    :param path_dict:
    """
    paths_to_delete = []
    for old_path in list(path_dict.keys()):
        http_operations = path_dict[old_path]
        if '?' in old_path:
            paths_array = re.split('\?', old_path)
            new_path = paths_array[0]

            query_param = []
            for query_parameter in paths_array[1].split('&'):
                key_value = query_parameter.split('=')
                q_param = {'name': key_value[0], 'in': 'query', 'description': key_value[0] + '=' + key_value[1],
                        'required': True, 'type': 'string', 'enum': [key_value[1]]}
                query_param.append(q_param)

            if new_path in path_dict:
                new_path_operations = path_dict[new_path].keys()
                path_operations = http_operations.keys()
                if len(set(path_operations).intersection(new_path_operations)) < 1:
                    for http_method, operation_dict in http_operations.items():
                        operation_dict['parameters'] = operation_dict['parameters'] + query_param
                    path_dict[new_path] = merge_dictionaries(http_operations, path_dict[new_path])
                    paths_to_delete.append(old_path)
            else:
                for http_method, operation_dict in http_operations.items():
                    operation_dict['parameters'].append(q_param)
                path_dict[new_path] = path_dict.pop(old_path)
    for path in paths_to_delete:
        del path_dict[path]

def merge_dictionaries(x, y):
    z = x.copy()   # start with x's keys and values
    z.update(y)    # modifies z with y's keys and values & returns None
    return z