import six
import re
from lib import utils

class urlProcessing():

    def __init__(self):
        pass
    
    def find_url(self,list_of_links):
        """
        There are many apis which get same work done.
        The idea here is to show the best one.
        Here is the logic for picking the best one.
        * if there is only one element in the list, the choice is obvious.
        * if there are more than one:
            return for a link which does not contain "~action" in them and which contain "id:{}" in them.
        """
        if len(list_of_links) == 1:
            return list_of_links[0]['href'], list_of_links[0]['method']

        non_action_link = None
        for link in list_of_links:
            if '~action=' not in link['href']:
                if "id:" in link['href']:
                    return link['href'], link['method']
                if non_action_link is None:
                    non_action_link = link
        if non_action_link is None:
            # all links have ~action in them. check if any of them has id: and return it.
            for link in list_of_links:
                if "id:" in link['href']:
                    return link['href'], link['method']

            # all links have ~action in them and none of them have id: (pick any one)
            return list_of_links[0]['href'], list_of_links[0]['method']

        return non_action_link['href'], non_action_link['method']

    def get_service_path_from_service_url(self,service_url, base_url):
        if not service_url.startswith(base_url):
            return service_url
        return service_url[len(base_url):]

    def convert_path_list_to_path_map(self,path_list):
        """
        The same path can have multiple methods.
        For example: /vcenter/vm can have 'get', 'patch', 'put'
        Rearrange list into a map/object which is the format expected by swagger-ui
        key is the path ie. /vcenter/vm/
        value is a an object which contains key as method names and value as path objects
        """
        path_dict = {}
        for path in path_list:
            x = path_dict.get(path['path'])
            if x is None:
                x = {path['method']: path}
                path_dict[path['path']] = x
            else:
                x[path['method']] = path
        return path_dict


    def cleanup(self,path_dict, type_dict):
        for _, type_object in six.iteritems(type_dict):
            if 'properties' in type_object or 'additionalProperties' in type_object:

                if 'properties' in type_object:
                    properties = type_object['properties']
                else:
                    properties = type_object['additionalProperties']

                for key, property_value in properties.items():
                    if isinstance(property_value, dict):
                        if 'required' in property_value and isinstance(property_value['required'], bool):
                            del property_value['required']
                        
        for _, path_value in six.iteritems(path_dict):
            for _, method_value in six.iteritems(path_value):
                if 'path' in method_value:
                    del method_value['path']
                if 'method' in method_value:
                    del method_value['method']

class pathProcessing():
    def __init__(self):
        pass

    def remove_com_vmware_from_dict(self, swagger_obj, depth=0, keys_list=[]):
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
                        self.remove_com_vmware_from_dict(itm, depth+1, keys_list)
                elif isinstance(item, dict):
                    if depth == 0 and isinstance(key, str) and (key.startswith('com.vmware.') or '$' in key):
                        keys_list.append(key)
                    self.remove_com_vmware_from_dict(item, depth+1, keys_list)
        elif isinstance(swagger_obj, list):
            for itm in swagger_obj:
                self.remove_com_vmware_from_dict(itm, depth+1)
        if depth == 0 and len(keys_list) > 0:
            while keys_list:
                old_key = keys_list.pop()
                new_key = old_key.replace('com.vmware.', '')
                new_key = new_key.replace('$', '_')
                try:
                    swagger_obj[new_key] = swagger_obj.pop(old_key)
                except KeyError:
                    print('Could not find the Swagger Element :  {}'.format(old_key))

    def create_unique_op_ids(self, path_dict):
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
                op_id_val = self.create_camelized_op_id(path, http_method, operation_dict)
                if op_id_val not in op_id_list:
                    operation_dict['operationId'] = op_id_val
                    op_id_list.append(op_id_val)    
    
    def create_camelized_op_id(self, path, http_method, operations_dict):
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
    
    def merge_dictionaries(self, x, y):
        z = x.copy()   # start with x's keys and values
        z.update(y)    # modifies z with y's keys and values & returns None
        return z
