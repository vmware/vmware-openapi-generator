import six
import re

class UrlProcessing():

    def __init__(self):
        pass

    def find_url(self, list_of_links):
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
            # all links have ~action in them. check if any of them has id: and
            # return it.
            for link in list_of_links:
                if "id:" in link['href']:
                    return link['href'], link['method']

            # all links have ~action in them and none of them have id: (pick
            # any one)
            return list_of_links[0]['href'], list_of_links[0]['method']

        return non_action_link['href'], non_action_link['method']

    def get_service_path_from_service_url(self, service_url, base_url):
        if not service_url.startswith(base_url):
            return service_url
        return service_url[len(base_url):]

    def convert_path_list_to_path_map(self, path_list):
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

    def cleanup(self, path_dict, type_dict):
        for _, type_object in six.iteritems(type_dict):
            if 'properties' in type_object or 'additionalProperties' in type_object:

                if 'properties' in type_object:
                    properties = type_object['properties']
                else:
                    properties = type_object['additionalProperties']

                for key, property_value in properties.items():
                    if isinstance(property_value, dict):
                        if 'required' in property_value and isinstance(
                                property_value['required'], bool):
                            del property_value['required']

        for _, path_value in six.iteritems(path_dict):
            for _, method_value in six.iteritems(path_value):
                if 'path' in method_value:
                    del method_value['path']
                if 'method' in method_value:
                    del method_value['method']
