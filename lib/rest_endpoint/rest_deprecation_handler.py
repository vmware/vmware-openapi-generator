# Copyright 2020 VMware, Inc.
# SPDX-License-Identifier: MIT

class RestDeprecationHandler:

    def __init__(self, replacement_dict):
        '''
        service -> operation -> (method, raplacement path) ; for deprecated /rest
        '''
        self.replacement_dict = replacement_dict

    def add_deprecation_information(self, path_obj, package_name, service_name):
        method = None
        new_path = None
        # Could be a more intelligent resolution - guessing based on key words?
        operation_map = self.replacement_dict.get(service_name)
        if operation_map is not None and "operationId" in path_obj:
            method_path_tuple = operation_map.get(path_obj["operationId"])
            if method_path_tuple is not None:
                method = method_path_tuple[0]
                new_path = method_path_tuple[1]

        RestDeprecationHandler.add_deprecation_information_raw(path_obj, package_name, method, new_path)

    @staticmethod
    def add_deprecation_information_raw(path_obj, package_name, method, new_path):
        replacement_path = "<unknown>"
        path_obj["deprecated"] = True

        # construct file name
        api_file_name = package_name + ".json"

        if method is not None and new_path is not None:
            replacement_path = api_file_name + "#/paths/~1api" + new_path.replace("/", "~1") + "/" + method

        path_obj["x-vmw-deprecated"] = {"replacement": replacement_path}
