# vmware-openapi-generator

## Overview
vmware-openapi-generator generates OpenAPI/Swagger documents from vAPI metamodel format.

This generator can be used to work with an existing vCenter Server (6.5+) to generate a OpenAPI/Swagger document based on the REST APIs which exist as part of that server.

## Try it out

### Prerequisites

* Install VMware vSphere Automation SDK for Python at https://github.com/vmware/vsphere-automation-sdk-python  


### Build & Run

```  
python vmsgen.py -vc <vCenter IP> -o <output directory path>  
```    
```
Trying to connect https://vcip/api 
Connected to https://vcip/api 			  
processing package vcenter  
processing package cis  
processing package appliance  
processing package vapi  
processing package content  
Generated swagger files at output for https://vcip/api in 106.460405666999577 seconds    
```

Running the above command generates the openAPI specification files (3.0) by default. In order to generate the swagger 2.0 specification files, the parameter -oas needs to passed explicitly.

The description of the input parameters that can go in the run command is as follows:
1. **metadata-url** : It is the url of the metadata API. If IP address of the vCenter (vcip) is provided, it takes in the values as **https://< vcip >/api**
2. **rest-navigation-url**: This is the url for rest navigation. If vcip is provided this url becomes **https://< vcip >/rest**
3. **vcip**: It is the IP Address of the vCenter server. It is used to specify the metadata-url and rest-navigation-url.
4. **output**: This is output directory where the generated swagger or openapi files will be stored. If the output directory is not supplied, the present working directory is chosen as the output directory.
5. **tag-seperator**: It is the seperator to be used in tag names i.e. '/'.
6. **insecure**: It is used to check the SSL certificate validation. If this parameter is supplied as an input argument, it bypasses the certificate validation. If not passed, the program will check for validation.
7. **unique-operation-ids**: This parameter is passed to generate unique ids for all operation/functions. Default value of this parameter is false. A required semantic rule of the open api specification is that the operations should have a unique operation name even if they are under different paths. If this parameter is ignored the generated swagger file may throw semantic error if it fails the openapi validation.
8. **metamodel-components**: If this parameter is passed, then each metamodel component retreived from the vCenter server is saved in a different .json file under the metamodel directory.
9. **host**: It is the IP Address of the host that serves the API. By default the value is < vcenter >
10. **enable-filtering**: It is used to filter out internal and unrealeased API's so that if service info of the API is still under modification, it is skipped for processing.
11. **oas** : This parameter is used to specify as to which version of swagger file the user wants to generate. By default the generated files are of version 3 i.e openapi. If the user wants to generate the version 2 files, the parameter needs to be passed explicitly.
12. **mixed** : This parameter is used to specify whether deprecated APIs are going to be generated. By default the generated files do not contain information regarding the deprecated "/rest" APIs. If the user wants that information to be apparent in the generated files, then the parameter needs to be passed.

## Contributing

The vmware-openapi-generator project team welcomes contributions from the community. Before you start working with vmware-openapi-generator, please read our [Developer Certificate of Origin](https://cla.vmware.com/dco). All contributions to this repository must be signed as described on that page. Your signature certifies that you wrote the patch or have the right to pass it on as an open-source patch. For more detailed information, refer to [CONTRIBUTING.md](CONTRIBUTING.md).

## License
MIT License

Copyright (c)  2016-2020 VMware, Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
