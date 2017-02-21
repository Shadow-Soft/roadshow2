#!/usr/bin/python
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
DOCUMENTATION = '''
--- 
author: "Derrick Sutherland"
description: 
  - "Capture an Azure Virtual Machine image to create other virtual machines with. You must run the command 
    'sudo waagent -deprovision+user -force' on the target machine before calling this module. This could be accomplished using the deprovision task in manage-azure.  After this command runs, the Virtual Machine will be unusable. 
	Depends on pip azure module 2.0 or above"
module: azure_image_capture
options: 
  resource_group_name: 
    description: 
      - "The resource group name to use or create to host the deployed template"
    required: true
  subscription_id: 
    description: 
      - "The Azure subscription to deploy the template into."
    required: true
  tenant_id: 
    description: 
      - "The Azure Active Directory tenant ID of the subscription."
    required: true
  client_id: 
    description: 
      - "The Azure Active Directory tenant ID of the subscription."
    required: true
  destination_container: 
    description: 
      - "The destination within the VM storage account to copy the image."
    required: true
  vm_name: 
    description: 
      - "The name of the VM within the resource group to capture"
    required: true
short_description: "Capture Azure Virtual Machine Images"
version_added: "2.0"

'''

EXAMPLES = '''
# Genercize a VM
# use the azure_deploy module to deploy azure instances and add as hosts
- name: Run Deprovision user Command
  hosts: launched
  remote_user: "{{admin_user}}"
  tasks:
    - name: Deprovision User
      command: sudo waagent -deprovision+user -force
- name: Genericize
  hosts: 127.0.0.1
  connection: local
  tasks:
    - name: Genercize VM
      local_action:
        module: azure_image_capture 
        subscription_id: "{{subscription_id}}"
        resource_group_name: '{{resource_group_name}}'
        destination_container: copiedvhds
        client_id: "{{client_id}}"
        tenant_id: "{{tenant_id}}"
        client_secret: "{{client_secret}}" # don't check in!
        vm_name: "{{vm_name}}"
        wait: "{{wait}}"
      register: capture_info
- debug: capture_info
# ok: [127.0.0.1] => {
#     "var": {
#         "capture_info": {
#             "changed": false,
#             "invocation": {
#                 "module_args": "",
#                 "module_complex_args": {
#                     "client_id": "CLIENT_ID",
#                     "client_secret": "CLIENT_SECRET",
#                     "destination_container": "copiedvhds",
#                     "resource_group_name": "sedouardcaptur22",
#                     "subscription_id": "SUBSCRIPTION_ID",
#                     "tenant_id": "TENANT_ID",
#                     "vm_name": "MyUbuntuVM"
#                 },
#                 "module_name": "azure_image_capture"
#             },
#             "msg": "Sucessfully captured image to container:copiedvhds",
#             "vhd_uri": "http://ib52izs3mc4ki.blob.core.windows.net/system/Microsoft.Compute/Images/copiedvhds/vm-osdisk-osDisk.bef24ae1-de36-4038-8e78-7df443e3d255.vhd"
#         }
#     }
# }

# Deploy a VM, Capture and copy to other Storage Accounts with azure_copy_blob
- name: Genericize
  hosts: 127.0.0.1
  connection: local
  vars:
    storage_accounts:
      -
        account_name: storageaccount1
        key: storageaccountkey123123213232132123
        container: storedimages
        blob: graphstoryneo4j.vhd
      -
        account_name: storageaccount2
        key: storageaccountkey123123213232132123
        container: storedimages
        blob: graphstoryneo4j.vhd
      -
        account_name: storageaccount3
        key: storageaccountkey123123213232132123
        container: storedimages
        blob: graphstoryneo4j.vhd
  tasks:
    - name: Genercize VM
      local_action:
        module: azure_image_capture 
        subscription_id: "{{subscription_id}}"
        resource_group_name: '{{resource_group_name}}'
        destination_container: copiedvhds
        client_id: "{{client_id}}"
        tenant_id: "{{tenant_id}}"
        client_secret: "{{client_secret}}" # don't check in!
        vm_name: "{{vm_name}}"
        wait: True
      register: capture_info
    - name: Copy Blob
      local_action:
        module: azure_copy_blob
        source_uri: "{{source_vhd_uri}}"
        source_key: "{{azure.outputs.storage_key.value.key1}}"
        destination_account: "{{item.account_name}}"
        destination_container: "{{item.container}}"
        destination_key: "{{item.key}}"
        destination_blob: "{{item.blob}}"
      with_items: storage_accounts

'''
import time
import yaml

HAS_DEPS = True
HAS_DEPS_EXC = None

try:
    from azure.mgmt.compute import ComputeManagementClient
    from azure.mgmt.compute.models import VirtualMachineCaptureParameters
    from azure.common.credentials import ServicePrincipalCredentials
except ImportError as exc:
    HAS_DEPS_EXC = exc
    HAS_DEPS = False

class ConfigurationHelper(object):
    @staticmethod
    def get_azure_connection_info(module):
        azure_url = module.params.get('azure_url')
        tenant_id = module.params.get('tenant_id')
        client_id = module.params.get('client_id')
        vhd_prefix = module.params.get('vhd_prefix')
        client_secret = module.params.get('client_secret')
        vm_name = module.params.get('vm_name')
        destination_container = module.params.get('destination_container')
        resource_group_name = module.params.get('resource_group_name')
        subscription_id = module.params.get('subscription_id')

        if azure_url is None:
           azure_url = os.environ.get('AZURE_URL', None)
        if resource_group_name is None:
           resource_group_name = os.environ.get('AZURE_RESOURCE_GROUP_NAME', None)
        if destination_container is None:
           destination_container = os.environ.get('DESTINATION_CONTAINER', None)
        if subscription_id is None:
           subscription_id = os.environ.get('AZURE_SUBSCRIPTION_ID', None)
        if tenant_id is None:
           tenant_id = os.environ.get('AZURE_TENANT', None)
        if client_id is None:
           client_id = os.environ.get('AZURE_CLIENT_ID', None)
        if client_secret is None:
           client_secret = os.environ.get('AZURE_SECRET', None)

        return dict(azure_url=azure_url,
                    tenant_id=tenant_id,
                    client_id=client_id,
                    client_secret=client_secret,
                    destination_container=destination_container,
                    vm_name=vm_name,
                    vhd_prefix=vhd_prefix,
                    resource_group_name=resource_group_name,
                    subscription_id=subscription_id)
    @staticmethod
    def validate_configuration(conn_info,module):
        if conn_info['client_id'] is None or conn_info['client_secret'] is None or conn_info['tenant_id'] is None or conn_info['subscription_id'] is None:
           module.fail_json(msg='security token or client_id, client_secret, subscription_id and tenant_id is required')

class Capture(object):
    def __init__(self, 
        subscription_id, 
        client_id, 
        tenant_id, 
        secret,
        resource_group_name):
    
        credentials = ServicePrincipalCredentials(
          client_id = client_id,
          secret = secret,
          tenant = tenant_id
        )

        self._resource_group_name = resource_group_name

        self._client = ComputeManagementClient(credentials, subscription_id)


    def captureImages(self, 
    destination_container_name,
    vhd_prefix,
    vm_name,
    overwrite=False):

        vmOps = self._client.virtual_machines
        params = VirtualMachineCaptureParameters(vhd_prefix, destination_container_name, overwrite)
        vmOps.deallocate(self._resource_group_name, vm_name).wait()
        vmOps.generalize(self._resource_group_name, vm_name)
        operation = vmOps.capture(self._resource_group_name, vm_name, params)
        operation.wait()
        result = operation.result()
        blob_uri = result.output['resources'][0]['properties']['storageProfile']['osDisk']['image']['uri']

        return blob_uri
def main():
    argument_spec = dict(
        subscription_id=dict(),
        client_secret=dict(no_log=True),
        client_id=dict(),
        tenant_id=dict(),
        resource_group_name=dict(required=True),
        vm_name=dict(required=True),
        destination_container=dict(required=True),
        vhd_prefix=dict(default="vm-osdisk")
    )
    module = AnsibleModule(
        argument_spec=argument_spec
    )

    if not HAS_DEPS:
        module.fail_json(msg="requests and azure are required for this module ".format(HAS_DEPS_EXC))

    conn_info = ConfigurationHelper.get_azure_connection_info(module)
    ConfigurationHelper.validate_configuration(conn_info,module)

    imageCapture = Capture(conn_info['subscription_id'], 
        conn_info['client_id'],
        conn_info['tenant_id'],
        conn_info['client_secret'],
        conn_info['resource_group_name'])

    vhd_uri = imageCapture.captureImages(
        conn_info['destination_container'],
        conn_info['vhd_prefix'],
        conn_info['vm_name'],
        True)

    data = dict(msg='Sucessfully captured image to container:' + conn_info['destination_container'],
        vhd_uri=vhd_uri)
    module.exit_json(**data)

# import module snippets
from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()