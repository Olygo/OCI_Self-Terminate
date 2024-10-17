This script requests the termination of the instance on which it is executed.
For the instance to request its own termination, it must authenticate with the OCI API.
To enable this, you need to create a Dynamic Group (e.g., DG_self_termination) that includes "All {instance.compartment.id = 'xxxxx'}".
Additionally, you'll need a policy with at least the following statement:

    allow dynamic-group DG_self_termination to manage instance-family in compartment XXXXX where request.operation='TerminateInstance'	

or

    allow dynamic-group DG_self_termination to manage instance-family in compartment XXXXX where any {request.operation='TerminateInstance',request.permission='INSTANCE_DELETE',request.permission='VOLUME_DELETE',request.permission='VNIC_DELETE',request.permission='SUBNET_DETACH',request.permission='VOLUME_WRITE',request.permission='INSTANCE_DETACH_VOLUME',request.permission='VOLUME_ATTACHMENT_DELETE'}
    allow dynamic-group DG_self_termination to manage instance-family in compartment XXXXX where any {request.operation='TerminateInstance',request.permission='INSTANCE_READ',request.permission='INSTANCE_DELETE',request.permission='VOLUME_DELETE',request.permission='VNIC_DELETE',request.permission='SUBNET_DETACH',request.permission='VOLUME_WRITE',request.permission='INSTANCE_DETACH_VOLUME',request.permission='VOLUME_ATTACHMENT_DELETE'}

**Instance prerequisites:**

    python3 -m pip install pip -U --user
    python3 -m pip install wheel oci requests -U --user

**Usage:**

    python3 ./OCI_Self-Terminate.py

**Disclaimer:**

This script is an independent tool developed by 
Florian Bonneville and is not affiliated with or 
supported by Oracle. It is provided as-is and without 
any warranty or official endorsement from Oracle
- - - - - - - - - - - - - - - - - - - - - - - - - - - -
