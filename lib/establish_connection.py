import argparse
import os
from vmware.vapi.stdlib.client.factories import StubConfigurationFactory
from com.vmware.vapi.metadata import metamodel_client
from com.vmware.vapi.metadata import authentication_client


def get_input_params():
    """
    Gets input parameters from command line
    :return:
    """
    parser = argparse.ArgumentParser(
        description='Generate swagger.json files for apis on vcenter')
    parser.add_argument('-m', '--metadata-url', help='URL of the metadata API')
    parser.add_argument(
        '-rn',
        '--rest-navigation-url',
        help='URL of the rest-navigation API')
    parser.add_argument(
        '-vc',
        '--vcip',
        help='IP Address of vCenter Server. If specified, would be used'
        ' to calculate metadata-url and rest-navigation-url')
    parser.add_argument(
        '-o', '--output', help='Output directory of swagger files. if not specified,'
        ' current working directory is chosen as output directory')
    parser.add_argument(
        '-s',
        '--tag-separator',
        default='/',
        help='Separator to use in tag name')
    parser.add_argument(
        '-k',
        '--insecure',
        action='store_true',
        help='Bypass SSL certificate validation')
    parser.add_argument(
        "-uo",
        "--unique-operation-ids",
        required=False,
        nargs='?',
        const=True,
        default=False,
        help="Pass this parameter to generate Unique Operation Ids.")
    parser.add_argument(
        "-c",
        "--metamodel-components",
        required=False,
        nargs='?',
        const=True,
        default=False,
        help="Pass this parameter to save each metamodel component as a new json file")
    parser.add_argument(
        '--host',
        help='Domain name or IP address (IPv4) of the host that serves the API. '
        'Default value is "<vcenter>"')
    parser.add_argument(
        '-su',
        '--show-unreleased',
        required=False,
        nargs='?',
        const=True,
        default=False,
        dest='show_unreleased_apis',
        help='Includes internal and unreleased apis')
    parser.add_argument(
        '-oas',
        '--oas',
        default='3',
        help='opeanpi specification version')
    parser.add_argument(
        '-dsr',
        '--deprecate-slash-rest',
        required=False,
        nargs='?',
        const=True,
        default=False,
        dest='deprecate_rest',
        help='/api and /rest rendering - with /rest being deprecated')
    args = parser.parse_args()
    metadata_url = args.metadata_url
    rest_navigation_url = args.rest_navigation_url
    vcip = args.vcip
    if vcip is not None:
        if metadata_url is None:
            metadata_url = 'https://%s/api' % vcip
        if rest_navigation_url is None:
            rest_navigation_url = 'https://%s/rest' % vcip

    if metadata_url is None or rest_navigation_url is None:
        raise ValueError(
            'metadataUrl and restNavigationUrl are required parameters')
    metadata_url = metadata_url.rstrip('/')
    rest_navigation_url = rest_navigation_url.rstrip('/')
    output_dir = args.output
    if args.host is not None:
        global API_SERVER_HOST
        API_SERVER_HOST = args.host
    if output_dir is None:
        output_dir = os.getcwd()
    verify = not args.insecure

    global GENERATE_UNIQUE_OP_IDS
    GENERATE_UNIQUE_OP_IDS = args.unique_operation_ids

    global TAG_SEPARATOR
    TAG_SEPARATOR = args.tag_separator

    global show_unreleased_apis
    show_unreleased_apis = args.show_unreleased_apis

    global GENERATE_METAMODEL
    GENERATE_METAMODEL = args.metamodel_components

    global SPECIFICATION
    if args.oas not in ['2', '3']:
        raise Exception(" Input Valid Specification ")
    SPECIFICATION = args.oas

    global DEPRECATE_REST
    DEPRECATE_REST = args.deprecate_rest

    return metadata_url, rest_navigation_url, output_dir, verify, show_unreleased_apis, GENERATE_METAMODEL, SPECIFICATION, GENERATE_UNIQUE_OP_IDS, TAG_SEPARATOR, DEPRECATE_REST


def get_component_service(connector):
    stub_config = StubConfigurationFactory.new_std_configuration(connector)
    component_svc = metamodel_client.Component(stub_config)
    return component_svc

def get_authentication_component_service(connector):
    stub_config = StubConfigurationFactory.new_std_configuration(connector)
    component_svc = authentication_client.Component(stub_config)
    return component_svc