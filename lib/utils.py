import requests
import json
import sys
from six.moves import http_client

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def build_error_map():
    """
    Builds error_map which maps vapi errors to http status codes.
    """
    error_map = {'com.vmware.vapi.std.errors.already_exists': http_client.BAD_REQUEST,
                 'com.vmware.vapi.std.errors.already_in_desired_state': http_client.BAD_REQUEST,
                 'com.vmware.vapi.std.errors.feature_in_use': http_client.BAD_REQUEST,
                 'com.vmware.vapi.std.errors.internal_server_error':http_client.INTERNAL_SERVER_ERROR,
                 'com.vmware.vapi.std.errors.invalid_argument':http_client.BAD_REQUEST,
                 'com.vmware.vapi.std.errors.invalid_element_configuration':http_client.BAD_REQUEST,
                 'com.vmware.vapi.std.errors.invalid_element_type': http_client.BAD_REQUEST,
                 'com.vmware.vapi.std.errors.invalid_request': http_client.BAD_REQUEST,
                 'com.vmware.vapi.std.errors.not_found': http_client.NOT_FOUND,
                 'com.vmware.vapi.std.errors.operation_not_found': http_client.NOT_FOUND,
                 'com.vmware.vapi.std.errors.not_allowed_in_current_state': http_client.BAD_REQUEST,
                 'com.vmware.vapi.std.errors.resource_busy': http_client.BAD_REQUEST,
                 'com.vmware.vapi.std.errors.resource_in_use': http_client.BAD_REQUEST,
                 'com.vmware.vapi.std.errors.resource_inaccessible': http_client.BAD_REQUEST,
                 'com.vmware.vapi.std.errors.service_unavailable': http_client.SERVICE_UNAVAILABLE,
                 'com.vmware.vapi.std.errors.timed_out': http_client.GATEWAY_TIMEOUT,
                 'com.vmware.vapi.std.errors.unable_to_allocate_resource': http_client.BAD_REQUEST,
                 'com.vmware.vapi.std.errors.unauthenticated': http_client.UNAUTHORIZED,
                 'com.vmware.vapi.std.errors.unauthorized': http_client.FORBIDDEN,
                 'com.vmware.vapi.std.errors.unexpected_input': http_client.BAD_REQUEST,
                 'com.vmware.vapi.std.errors.unsupported': http_client.BAD_REQUEST,
                 'com.vmware.vapi.std.errors.error': http_client.BAD_REQUEST,
                 'com.vmware.vapi.std.errors.concurrent_change': http_client.BAD_REQUEST,
                 'com.vmware.vapi.std.errors.unverified_peer': http_client.BAD_REQUEST}
                 
    return error_map

def get_json(url, verify=True):
    try:
        req = requests.get(url, verify=verify)
    except Exception as ex:
        eprint('Cannot Load %s - %s' % (url, req.content))
        eprint(ex)
        return None
    if not req.ok:
        eprint('Cannot Load %s - %s' % (url, req.content))
        return None
    if 'value' in req.json():
        return req.json()['value']
    return req.json()


def write_json_data_to_file(file_name, json_data):
    """
    Utility method used to write json file.
    """
    with open(file_name, 'w+') as outfile:
        json.dump(json_data, outfile, indent=4)

def load_description():
    """
    Loads description.properties into a dictionary.
    """
    desc = {
        'content': 'VMware vSphere\u00ae Content Library empowers vSphere Admins to effectively manage VM templates, '
                   'vApps, ISO images and scripts with ease.', 'spbm': 'SPBM',
        'vapi': 'vAPI is an extensible API Platform for modelling and delivering APIs/SDKs/CLIs.',
        'vcenter': 'VMware vCenter Server provides a centralized platform for managing your VMware vSphere environments'
        , 'appliance': 'The vCenter Server Appliance is a preconfigured Linux-based virtual machine'
          ' optimized for running vCenter Server and associated services.'}
    return desc

def is_filtered(metadata, enable_filtering):
    if not enable_filtering:
        return False
    if len(metadata) == 0:
        return False
    if 'TechPreview' in metadata:
        return False
    if 'Changing' in metadata or 'Proposed' in metadata:
        return True
    return False