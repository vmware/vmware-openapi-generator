class RestDeprecationHandler:

    def __init__(self, replacement_map):
        '''
        The replacement navigation map is used when MIXED specification is issued (@VERB + an old annotation standard)
        It contains mappings to url paths, served as replacements. The structure of the map is the following:
        service -> operation -> method -> raplacement path
        '''
        self.replacement_map = replacement_map

    def add_deprecation_information(self, path_obj, package_name, service_name):
        replacement_path = "<unknown>"
        path_obj["deprecated"] = True

        # construct file name
        api_file_name = "api_" + package_name + ".json"

        # Could be a more intelligent resolution - guessing based on key words?
        operation_map = self.replacement_map.get(service_name)
        if operation_map is not None and "operationId" in path_obj:
            method_map = operation_map.get(path_obj["operationId"])
            if method_map is not None and "method" in path_obj:
                # get concrete path and format accordingly
                replacement_path = method_map.get(path_obj["method"])
                replacement_path = replacement_path.replace("/", "~1")
                replacement_path = api_file_name + "#/paths/" + replacement_path + "/" + path_obj["method"]

        path_obj["x-vmw-deprecated"] = {"replacement": replacement_path}

