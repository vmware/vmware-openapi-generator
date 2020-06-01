import os

import six

from lib import utils
from lib.openapi_final_path_processing import OpenapiPathProcessing
from lib.swagger_final_path_processing import SwaggerPathProcessing


class FileOutputHandler:

    swagg = SwaggerPathProcessing()
    openapi = OpenapiPathProcessing()

    def __init__(self,
                 rest_package_spec_dict,
                 api_package_spec_dict,
                 output_dir,
                 gen_unique_op_id,
                 spec,
                 split_api_rest=True):
        self.rest_package_spec_dict = rest_package_spec_dict
        self.api_package_spec_dict = api_package_spec_dict
        self.output_dir = output_dir
        self.gen_unique_op_id = gen_unique_op_id
        self.spec = spec
        self.split_api_rest = split_api_rest

    def __output_spec(self, package_name, path_dict, type_dict, file_prefix=''):
        if self.spec == '2':
            self.swagg.process_output(
                path_dict,
                type_dict,
                self.output_dir,
                package_name,
                self.gen_unique_op_id,
                file_prefix)
        if self.spec == '3':
            self.openapi.process_output(
                path_dict,
                type_dict,
                self.output_dir,
                package_name,
                self.gen_unique_op_id,
                file_prefix)

    def __produce_merged(self):
        merger = SpecificationDictsMerger(self.rest_package_spec_dict.copy(),
                                          self.api_package_spec_dict.copy())
        merged_dict = merger.merge_api_rest_dicts()
        for package, path_type_tuple in six.iteritems(merged_dict):
            self.__output_spec(package, path_type_tuple[0], path_type_tuple[1])

    def __produce_split(self):
        for package, path_type_tuple in six.iteritems(self.rest_package_spec_dict):
            self.__output_spec(package, path_type_tuple[0], path_type_tuple[1], "rest")
        for package, path_type_tuple in six.iteritems(self.api_package_spec_dict):
            self.__output_spec(package, path_type_tuple[0], path_type_tuple[1], "api")

    def __produce_api_json(self):
        # api.json contains list of packages which is used by UI to dynamically
        # populate dropdown.
        api_files_list = []
        for name in list(self.rest_package_spec_dict.keys()):
            if self.split_api_rest:
                api_files_list.append("rest_" + name)
            else:
                api_files_list.append(name)
        for name in list(self.api_package_spec_dict.keys()):
            if self.split_api_rest:
                api_files_list.append("api_" + name)
            else:
                api_files_list.append(name)

        api_files = {'files': api_files_list}
        utils.write_json_data_to_file(
            self.output_dir +
            os.path.sep +
            'api.json',
            api_files)

    def output_files(self):
        if self.split_api_rest:
            self.__produce_split()
        else:
            self.__produce_merged()


class SpecificationDictsMerger:

    def __init__(self,
                 rest_package_spec_dict,
                 api_package_spec_dict):
        self.rest_package_spec_dict = rest_package_spec_dict
        self.api_package_spec_dict = api_package_spec_dict

    def merge_api_rest_dicts(self):
        for package, path_type_tuple in six.iteritems(self.api_package_spec_dict):
            if package in self.rest_package_spec_dict:
                self.__merge_path_dicts(self.rest_package_spec_dict[package][0], path_type_tuple[0])
                self.__merge_type_dicts(self.rest_package_spec_dict[package][1], path_type_tuple[1])
            else:
                self.rest_package_spec_dict[package] = path_type_tuple
        return self.rest_package_spec_dict

    def __merge_path_dicts(self, path_dict_extended, path_dict_added):
        # Since paths begin either with /api or /rest, no collisions are expected
        path_dict_extended.update(path_dict_added)

    def __merge_type_dicts(self, type_dict_extended, type_dict_added):
        for type_name, type_def_dict in six.iteritems(type_dict_added):
            if type_name in type_dict_extended:
                # Existing definitions may contain discrepancies, hence they need to be preserved
                type_dict_extended[type_name + "_deprecated"] = type_dict_extended[type_name]
            type_dict_extended[type_name] = type_def_dict
