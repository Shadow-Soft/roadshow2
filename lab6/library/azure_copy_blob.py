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
author: "Steven Edouard (@sedouard)"
module: azure_copy_blob
short_description: Copy an Azure Blob
version_added: "2.0"
description:
     - Copy and Azure Blob from one container to another or one account to another. Depends on pip azure 2.0 or above package.
options:
  source_uri:
    description:
      - The source URI of the blob in the format 'https://{storage_account_name}.blob.core.windows.net/{container_name}/{blob_name}
  source_key:
    description:
      - The key for the source storage account
    required: true
  destination_account:
    description:
      - The name for the destination storage account 
    required: true
  destination_key:
    description:
      - The key for the destination storage account
    required: true
  destination_container:
    description:
      - The destination container which the blob will be opied to
    required: false
    default: None
  destination_blob:
    description:
      - The name of the destination blob that the source blob will be copied to.
    required: false
    default: None
  wait:
    description:
      - If set to True, will wait until the copy operation completes before returning.
    default: false
  timeout:
    description:
      - If wait is set to True, the amount of time to wait before a timeout error on the copy operation.
    default: 10000

'''

EXAMPLES = '''
# Copy a blob
- name: Copy Azure Storage Blob
  hosts: 127.0.0.1
  connection: local
  tasks:
    - name: Copy Blob
      local_action:
        module: azure_copy_blob
        source_uri: "http://storageaccountname.blob.core.windows.net/containername/blob.vhd"
        source_key: "someaccountkey12345"
        destination_account: "detinationaccountname"
        destination_container: "destinationcontainer"
        destination_key: "destinationkey"
        destination_blob: "desintationblob"
'''

try:
    import time
    import yaml
    import requests
    import azure
    from datetime import datetime, timedelta
    from itertools import chain
    from azure.storage.blob import BlockBlobService
    from azure.storage import CloudStorageAccount
    from azure.storage import Services
    from azure.storage import ResourceTypes
    from azure.storage import AccountPermissions

    import ansible.runner
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False

def split_uri(source_uri):
      # example: https://devopsclestorage3.blob.core.windows.net/vhds/osdiskforlinuxsimple.vhd
      account = source_uri[(source_uri.index('://') + 3): (source_uri.index('blob.core.windows.net')) - 1]

      first_slash = source_uri.find('/', source_uri.index('://') + 3)
      container_end_slash = source_uri.find('/', first_slash + 1)
      container = source_uri[first_slash + 1: container_end_slash]

      blob = source_uri[container_end_slash + 1:len(source_uri)]

      return (account, container, blob)

def main():
    argument_spec = dict(
        source_uri=dict(required=True),
        source_key=dict(required=True),
        destination_account=dict(required=True),
        destination_key=dict(required=True),
        destination_container=dict(required=True),
        destination_blob=dict(required=True),
        wait=dict(default=False, type='bool'),
        timeout=dict(default=1000)
    )
    module = AnsibleModule(
        argument_spec=argument_spec
    )

    if not HAS_DEPS:
        module.fail_json(msg='requests and azure are required for this module')

    source_account, source_container, source_blob = split_uri(module.params.get('source_uri'))
    source = CloudStorageAccount(account_name=source_account, account_key=module.params.get('source_key'))
    source_service = source.create_block_blob_service()
    destination_service = BlockBlobService(account_name=module.params.get('destination_account'), 
                                            account_key=module.params.get('destination_key'))

    source_token = source.generate_shared_access_signature(Services.BLOB, 
        ResourceTypes.OBJECT, 
        AccountPermissions.READ, 
        datetime.utcnow() + timedelta(hours=1))
    source_sas_url = source_service.make_blob_url(source_container, source_blob, 'https', source_token)

    destination_service.create_container(module.params.get('destination_container'), fail_on_exist=False)
    status = destination_service.copy_blob(module.params.get('destination_container'), module.params.get('destination_blob'), source_sas_url)

    if not module.params.get('wait'):
        data = dict(changed=True, status='started')
        module.exit_json(**data)
    else:
        copy = destination_service.get_blob_properties(module.params.get('destination_container'), module.params.get('destination_blob')).properties.copy
        count = 0
        while copy.status != 'success':
            count = count + 30
            if count > module.params.get('timeout'):
                module.fail_json(msg='Timed out waiting for async copy to complete.')
            time.sleep(30)
            copy = destination_service.get_blob_properties(module.params.get('destination_container'), module.params.get('destination_blob')).properties.copy
        data = dict(changed=True, status='completed')
        module.exit_json(**data)
    

# import module snippets
from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()