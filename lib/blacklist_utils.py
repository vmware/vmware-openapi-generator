blacklist = {"rest": ['com.vmware.vcenter.vm.compute.policies',
                      'com.vmware.vcenter.compute.policies.tag_usage',
                      'com.vmware.vcenter.compute.policies.VM',
                      'com.vmware.vcenter.compute.policies.capabilities',
                      'com.vmware.vcenter.compute.policies'],
             "api": []}


def isBlacklistedForRest(service):
    return service in blacklist["rest"]


def isBlacklistedForApi(service):
    return service in blacklist["api"]
