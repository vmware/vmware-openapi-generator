import re

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
