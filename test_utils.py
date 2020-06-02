import unittest

from lib import utils


class TestUtils(unittest.TestCase):

    def test_combine_dicts_with_list_values(self):
        extended = {"1": ["1", "2", "3"],
                    "2": ["4", "5", "6"]}
        added = {"3": ["8", "9"],
                 "2": ["4", "5", "6", "7"]}

        utils.combine_dicts_with_list_values(extended, added)
        # Note after combining lists, the original order is not preserved
        extended.get("1").sort()
        extended.get("2").sort()
        extended.get("3").sort()
        self.assertEqual(extended.get("1"), ["1", "2", "3"])
        self.assertEqual(extended.get("2"), ["4", "5", "6", "7"])
        self.assertEqual(extended.get("3"), ["8", "9"])

    def test_recursive_ref_update(self):
        sample_dict = {'get': {'tags': ['vm/compute/policies'],
                               'summary': 'Returns information about the compliance of a virtual machine with a compute policy in VMware Cloud on AWS. Usage beyond VMware Cloud on AWS is not supported. Warning: This operation is available as Technology Preview. These are early access APIs provided to test, automate and provide feedback on the feature. Since this can change based on feedback, VMware does not guarantee backwards compatibility and recommends against using them in production environments. Some Technology Preview APIs might only be applicable to specific environments.',
                               'parameters': [{'type': 'string', 'required': True, 'in': 'path', 'name': 'vm',
                                               'description': 'Identifier of the virtual machine to query the status for.'},
                                              {'type': 'string', 'required': True, 'in': 'path', 'name': 'policy',
                                               'description': 'Identifier of the policy to query the status for.'}],
                               'responses': {
                                   200: {
                                       'description': 'Information about the compliance of the specified virtual machine with the specified compute policy.',
                                       'schema': {'$ref': '#/definitions/com.vmware.vcenter.vm.compute.policies.info'}},
                                   404: {
                                       'description': 'if a virtual machine with the given identifier does not exist, or if a policy with the given identifier does not exist.',
                                       'schema': {'$ref': '#/definitions/com.vmware.vapi.std.errors.not_found'}},
                                   403: {'description': "if the user doesn't have the required privileges.",
                                         'schema': {'$ref': '#/definitions/com.vmware.vapi.std.errors.unauthorized'}},
                                   401: {'description': "if the user doesn't have the required privileges.",
                                         'schema': {'$ref': '#/definitions/com.vmware.vapi.std.errors.unauthorized'}}
                               },

                               'operationId': 'get'}}
        old = '#/definitions/com.vmware.vcenter.vm.compute.policies.info'
        updated = '#/definitions/my.new.definition.resp'
        utils.recursive_ref_update(sample_dict, old, updated)
        self.assertEqual(sample_dict.get('get').get('responses').get(200).get('schema').get('$ref'), updated)
        old = '#/definitions/com.vmware.vapi.std.errors.unauthorized'
        updated = '#/definitions/my.new.definition.resp'
        utils.recursive_ref_update(sample_dict, old, updated)
        self.assertEqual(sample_dict.get('get').get('responses').get(401).get('schema').get('$ref'), updated)
        self.assertEqual(sample_dict.get('get').get('responses').get(403).get('schema').get('$ref'), updated)
        old = 'Identifier of the policy to query the status for.'
        updated = 'Some sample text...'
        utils.recursive_ref_update(sample_dict, old, updated)
        self.assertEqual(sample_dict.get('get').get('parameters')[1].get('description'), updated)

if __name__ == '__main__':
    unittest.main()
