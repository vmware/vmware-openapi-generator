import six

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

    def __merge_specs(self):
        pass

    def output_files(self):
        for package, path_type_tuple in six.iteritems(self.rest_package_spec_dict):
            self.__output_spec(package, path_type_tuple[0], path_type_tuple[1], "rest")
        for package, path_type_tuple in six.iteritems(self.api_package_spec_dict):
            self.__output_spec(package, path_type_tuple[0], path_type_tuple[1], "api")
