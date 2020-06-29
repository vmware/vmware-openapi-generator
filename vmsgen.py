'''
This script uses metamodel apis and rest navigation to generate openapi json files
for apis available on vcenter.
'''
from __future__ import print_function

from concurrent import futures

from lib import RestMetadataProcessor, authentication_metadata_processing
from lib import ApiMetadataProcessor
from lib import dictionary_processing as dict_processing
from lib import establish_connection as connection
from lib import utils
from vmware.vapi.core import ApplicationContext
from vmware.vapi.lib.constants import SHOW_UNRELEASED_APIS
from vmware.vapi.lib.connect import get_requests_connector
import timeit
import warnings
import requests
import six

from lib.authentication_metadata_processing import AuthenticationDictNavigator
from lib.file_output_handler import FileOutputHandler
from lib.rest_endpoint.rest_deprecation_handler import RestDeprecationHandler
from lib.rest_endpoint.rest_navigation_handler import RestNavigationHandler

warnings.filterwarnings("ignore")


GENERATE_UNIQUE_OP_IDS = False
GENERATE_METAMODEL = False
API_SERVER_HOST = ''
TAG_SEPARATOR = '/'
SPECIFICATION = '3'
DEPRECATE_REST = False


def main():
    # Get user input.
    metadata_api_url, \
    rest_navigation_url, \
    output_dir, \
    verify, \
    show_unreleased_apis, \
    GENERATE_METAMODEL, \
    SPECIFICATION, \
    GENERATE_UNIQUE_OP_IDS, \
    TAG_SEPARATOR, \
    DEPRECATE_REST = connection.get_input_params()
    # Maps enumeration id to enumeration info
    enumeration_dict = {}
    # Maps structure_id to structure_info
    structure_dict = {}
    # Maps service_id to service_info
    service_dict = {}
    # Maps service url to service id
    service_urls_map = {}

    rest_navigation_handler = RestNavigationHandler(rest_navigation_url)

    start = timeit.default_timer()
    print('Trying to connect ' + metadata_api_url)
    session = requests.session()
    session.verify = False
    connector = get_requests_connector(session, url=metadata_api_url)

    if show_unreleased_apis:
        connector.set_application_context(
            ApplicationContext({SHOW_UNRELEASED_APIS: "True"}))
    print('Connected to ' + metadata_api_url)
    component_svc = connection.get_component_service(connector)

    # Fetch authentication metadata and initialize the authentication data navigator
    auth_component_svc = connection.get_authentication_component_service(connector)
    auth_dict = authentication_metadata_processing.get_authentication_dict(auth_component_svc)
    auth_navigator = AuthenticationDictNavigator(auth_dict)

    dict_processing.populate_dicts(
        component_svc,
        enumeration_dict,
        structure_dict,
        service_dict,
        service_urls_map,
        rest_navigation_url,
        GENERATE_METAMODEL)

    http_error_map = utils.HttpErrorMap(component_svc)

    deprecation_handler = None

    # package_dict_api holds list of all service urls which come under /api
    # package_dict_deprecated holds a list of all service urls which come under /rest, but are
    # deprecated with /api
    # replacement_dict contains information about the deprecated /rest to /api mappings
    package_dict_api, package_dict, package_dict_deprecated, replacement_dict = dict_processing.add_service_urls_using_metamodel(
        service_urls_map, service_dict, rest_navigation_handler, DEPRECATE_REST)

    utils.combine_dicts_with_list_values(package_dict, package_dict_deprecated)
    if DEPRECATE_REST:
        deprecation_handler = RestDeprecationHandler(replacement_dict)

    rest = RestMetadataProcessor()
    api = ApiMetadataProcessor()

    rest_package_spec_dict = {}
    api_package_spec_dict = {}

    with futures.ThreadPoolExecutor() as executor:
        rest_package_future_dict = {package: executor.submit(
            rest.get_path_and_type_dicts,
            package,
            service_urls,
            structure_dict,
            enumeration_dict,
            service_dict,
            service_urls_map,
            http_error_map,
            rest_navigation_handler,
            show_unreleased_apis,
            SPECIFICATION,
            auth_navigator,
            deprecation_handler) for package, service_urls in
            six.iteritems(package_dict)
        }

        api_package_future_dict = {package: executor.submit(
            api.get_path_and_type_dicts,
            package,
            service_urls,
            structure_dict,
            enumeration_dict,
            service_dict,
            service_urls_map,
            http_error_map,
            show_unreleased_apis,
            SPECIFICATION,
            auth_navigator) for package, service_urls in
            six.iteritems(package_dict_api)
        }

        rest_package_spec_dict = {package: future.result() for package, future in
                                  six.iteritems(rest_package_future_dict)}
        api_package_spec_dict = {package: future.result() for package, future in
                                  six.iteritems(api_package_future_dict)}

    file_handler = FileOutputHandler(rest_package_spec_dict,
                                     api_package_spec_dict,
                                     output_dir,
                                     GENERATE_UNIQUE_OP_IDS,
                                     SPECIFICATION)
    file_handler.output_files()

    stop = timeit.default_timer()
    print('Generated swagger files at ' + output_dir + ' for ' +
          metadata_api_url + ' in ' + str(stop - start) + ' seconds')


if __name__ == '__main__':
    main()
