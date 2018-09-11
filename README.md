

# vmware-openapi-generator

## Overview
vmware-openapi-generator generates openapi/swagger documents from vapi metamodel format.  

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
Generated swagger files at /Users/sreeshas/PycharmProjects/vmsgen/output for https://vcip/api in 6.460405666999577 seconds    
```

## Contributing

The vmware-openapi-generator project team welcomes contributions from the community. Before you start working with vmware-openapi-generator, please read our [Developer Certificate of Origin](https://cla.vmware.com/dco). All contributions to this repository must be signed as described on that page. Your signature certifies that you wrote the patch or have the right to pass it on as an open-source patch. For more detailed information, refer to [CONTRIBUTING.md](CONTRIBUTING.md).

## License
MIT License

Copyright (c)  2016-2018 VMware, Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
