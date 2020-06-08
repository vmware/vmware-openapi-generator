import unittest

from lib import utils
from lib.file_output_handler import SpecificationDictsMerger


class TestSpecificationDictsMerger(unittest.TestCase):

    def test_merge_api_rest_dicts(self):
        rest_path_dict = {"/rest/com/vmware/vcenter/ovf/library_item":
            {"post": {
                "tags": [
                    "ovf/library_item"
                ],
                "parameters": [
                    {
                        "in": "body",
                        "name": "request_body",
                        "required": True,
                        "schema": {
                            "$ref": "#/definitions/com.vmware.vcenter.ovf.library_item_create"
                        }
                    }
                ],
                "responses": {
                    200: {
                        "schema": {
                            "$ref": "#/definitions/com.vmware.vcenter.ovf.library_item.create_resp"
                        }
                    },
                    400: {
                        "description": "if the specified virtual machine or virtual appliance is busy.",
                        "schema": {
                            "$ref": "#/definitions/com.vmware.vapi.std.errors.resource_busy_error"
                        }
                    },
                    404: {
                        "description": "if the virtual machine or virtual appliance specified by {@param.name source} does not exist.",
                        "schema": {
                            "$ref": "#/definitions/com.vmware.vapi.std.errors.not_found_error"
                        }
                    }
                },
                "operationId": "create"
            }
            },
            "/rest/com/vmware/vcenter/ovf/import_flag": {
                "get": {
                    "tags": [
                        "ovf/import_flag"
                    ],
                    "summary": "Returns information about the import flags supported by the deployment platform. <p> The supported flags are: <dl> <dt>LAX</dt> <dd>Lax mode parsing of the OVF descriptor.</dd> </dl> <p> Future server versions might support additional flags.",
                    "parameters": [
                        {
                            "type": "string",
                            "in": "query",
                            "name": "rp",
                            "description": "The identifier of resource pool target for retrieving the import flag(s).",
                            "required": True
                        }
                    ],
                    "responses": {
                        200: {
                            "description": "A {@term list} of supported import flags.",
                            "schema": {
                                "$ref": "#/definitions/com.vmware.vcenter.ovf.import_flag.list_resp"
                            }
                        },
                        404: {
                            "description": "If the resource pool associated with {@param.name rp} does not exist.",
                            "schema": {
                                "$ref": "#/definitions/com.vmware.vapi.std.errors.not_found_error"
                            }
                        }
                    },
                    "operationId": "list"
                }
            }
        }
        rest_type_dict = {"com.vmware.vcenter.ovf.import_flag.list_resp": {
            "type": "object",
            "properties": {
                "value": {
                    "type": "array",
                    "items": {
                        "$ref": "#/definitions/com.vmware.vcenter.ovf.import_flag.info"
                    }
                }
            },
            "required": [
                "value"
            ]
        }}

        # Use copies rather than references to the same dict
        api_path_dict = {
            "/api/com/vmware/vcenter/ovf/library_item": {"post": {
                "tags": [
                    "ovf/library_item"
                ],
                "parameters": [
                    {
                        "in": "body",
                        "name": "request_body",
                        "required": True,
                        "schema": {
                            "$ref": "#/definitions/com.vmware.vcenter.ovf.library_item_create"
                        }
                    }
                ],
                "responses": {
                    200: {
                        "schema": {
                            "$ref": "#/definitions/com.vmware.vcenter.ovf.library_item.create_resp"
                        }
                    },
                    400: {
                        "description": "if the specified virtual machine or virtual appliance is busy.",
                        "schema": {
                            "$ref": "#/definitions/com.vmware.vapi.std.errors.resource_busy_error"
                        }
                    },
                    404: {
                        "description": "if the virtual machine or virtual appliance specified by {@param.name source} does not exist.",
                        "schema": {
                            "$ref": "#/definitions/com.vmware.vapi.std.errors.not_found_error"
                        }
                    }
                },
                "operationId": "create"
            }
            },
            "/api/com/vmware/vcenter/ovf/import_flag": {
                "get": {
                    "tags": [
                        "ovf/import_flag"
                    ],
                    "summary": "Returns information about the import flags supported by the deployment platform. <p> The supported flags are: <dl> <dt>LAX</dt> <dd>Lax mode parsing of the OVF descriptor.</dd> </dl> <p> Future server versions might support additional flags.",
                    "parameters": [
                        {
                            "type": "string",
                            "in": "query",
                            "name": "rp",
                            "description": "The identifier of resource pool target for retrieving the import flag(s).",
                            "required": True
                        }
                    ],
                    "responses": {
                        200: {
                            "description": "A {@term list} of supported import flags.",
                            "schema": {
                                "$ref": "#/definitions/com.vmware.vcenter.ovf.import_flag.list_resp"
                            }
                        },
                        404: {
                            "description": "If the resource pool associated with {@param.name rp} does not exist.",
                            "schema": {
                                "$ref": "#/definitions/com.vmware.vapi.std.errors.not_found_error"
                            }
                        }
                    },
                    "operationId": "list"
                }
            },
            "/api/com/vmware/vcenter/ovf/export_flag": {}
        }
        api_type_dict = {"ComVmwareVcenterOvfImportFlag": {
            "type": "object",
            "properties": {
                "value": {
                    "type": "array",
                    "items": {
                        "$ref": "#/definitions/com.vmware.vcenter.ovf.import_flag.info"
                    }
                }
            },
            "required": [
                "value"
            ]
        }}

        rest_spec = {"vcenter": (dict(rest_path_dict), dict(rest_type_dict)),
                     "appliance": ({}, {})}
        api_spec = {"vcenter": (dict(api_path_dict), dict(api_type_dict)),
                    "cis": ({}, {})}

        merger = SpecificationDictsMerger(dict(rest_spec), dict(api_spec))
        merged = merger.merge_api_rest_dicts()
        self.assertTrue("vcenter" in merged and "cis" in merged and "appliance" in merged)
        self.assertEqual(len(merged["vcenter"][0]), 5)
        self.assertEqual(len(merged["vcenter"][1]), 2)
        api_def_type = merged["vcenter"][0] \
            .get("/api/com/vmware/vcenter/ovf/import_flag") \
            .get("get") \
            .get("responses") \
            .get(200) \
            .get("schema") \
            .get("$ref")
        self.assertEqual(api_def_type, "#/definitions/com.vmware.vcenter.ovf.import_flag.list_resp")


if __name__ == '__main__':
    unittest.main()
