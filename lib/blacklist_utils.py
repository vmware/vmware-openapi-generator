blacklist = {"rest": ['com.vmware.vcenter.vm.compute.policies',
                      'com.vmware.vcenter.compute.policies.tag_usage',
                      'com.vmware.vcenter.compute.policies.VM',
                      'com.vmware.vcenter.compute.policies.capabilities',
                      'com.vmware.vcenter.compute.policies'],
             "api": []}


def is_blacklisted_for_rest(service):
    return service in blacklist["rest"]


def is_blacklisted_for_api(service):
    return service in blacklist["api"]
