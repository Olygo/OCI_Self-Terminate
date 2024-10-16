# coding: utf-8

# - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# name: OCI_SelfTerminate.py
#
# Author: Florian Bonneville
# Version: 1.0.0 - Oct. 16, 2024
#
# This script requests the termination of the instance on which it is executed.
# For the instance to request its own termination, it must authenticate with the OCI API.
# To enable this, you need to create a Dynamic Group (e.g., DG_self_termination) that includes "All {instance.compartment.id = 'xxxxx'}".
# Additionally, you'll need a policy with at least the following statement:
#
# allow dynamic-group DG_self_termination to manage instance-family in compartment XXXXX where request.operation='TerminateInstance'	
# or
# allow dynamic-group DG_self_termination to manage instance-family in compartment XXXXX where any {request.operation='TerminateInstance',request.permission='INSTANCE_DELETE',request.permission='VOLUME_DELETE',request.permission='VNIC_DELETE',request.permission='SUBNET_DETACH',request.permission='VOLUME_WRITE',request.permission='INSTANCE_DETACH_VOLUME',request.permission='VOLUME_ATTACHMENT_DELETE'}
# allow dynamic-group DG_self_termination to manage instance-family in compartment XXXXX where any {request.operation='TerminateInstance',request.permission='INSTANCE_READ',request.permission='INSTANCE_DELETE',request.permission='VOLUME_DELETE',request.permission='VNIC_DELETE',request.permission='SUBNET_DETACH',request.permission='VOLUME_WRITE',request.permission='INSTANCE_DETACH_VOLUME',request.permission='VOLUME_ATTACHMENT_DELETE'}
#
# Disclaimer: 
# This script is an independent tool developed by 
# Florian Bonneville and is not affiliated with or 
# supported by Oracle. It is provided as-is and without 
# any warranty or official endorsement from Oracle
# - - - - - - - - - - - - - - - - - - - - - - - - - - - -

version="1.0.0"

import sys
import oci
import requests
import logging

def get_instance_metadata():
    url = "http://169.254.169.254/opc/v2/instance/"
    headers = {"Authorization": "Bearer Oracle"}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.RequestException as e:
        logging.error(f"Failed to fetch instance metadata:\n {e} \n")
        sys.exit(1)

    return response.json()

def log_instance_details(data):
    logging.info(f'Instance_Region: {data["canonicalRegionName"]}')
    logging.info(f'Instance_AD: {data["availabilityDomain"]}')
    logging.info(f'Instance_FD: {data["faultDomain"]}')
    logging.info(f'Instance_Name: {data["displayName"]}')
    logging.info(f'Instance_ID: {data["id"]}')
    logging.info(f'Instance_Shape: {data["shape"]}')

def terminate_instance(core_client, instance_id, custom_retry_strategy):
    try:
        core_client.terminate_instance(
            instance_id=instance_id,
            preserve_boot_volume=False,
            preserve_data_volumes_created_at_launch=False,
            retry_strategy=custom_retry_strategy
        )
        
        wait_termination = oci.wait_until(
            client=core_client,
            response=core_client.get_instance(instance_id),
            property='lifecycle_state',
            state='TERMINATING',
            max_wait_seconds=600
        )

        return wait_termination.data.lifecycle_state
    
    except oci.exceptions.ServiceError as e:
        logging.error(f"Failed to terminate instance:\n {e} \n")
        sys.exit(1)

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    custom_retry_strategy = oci.retry.RetryStrategyBuilder(
        max_attempts_check=True,
        max_attempts=8,
        total_elapsed_time_check=True,
        total_elapsed_time_seconds=600,
        retry_max_wait_between_calls_seconds=15,
        retry_base_sleep_time_seconds=15,
    ).get_retry_strategy()

    signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner(retry_strategy=custom_retry_strategy)
    config = {'region': signer.region, 'tenancy': signer.tenancy_id}

    print()
    logging.info("Fetching instance metadata...")
    instance_data = get_instance_metadata()

    if instance_data:
        log_instance_details(instance_data)
        instance_id = instance_data.get("id")
        if not instance_id:
            logging.error("Instance ID not found in metadata.\n")
            sys.exit(1)

        core_client = oci.core.ComputeClient(config=config, signer=signer)

        logging.info("Starting instance termination...")
        instance_state = terminate_instance(core_client, instance_id, custom_retry_strategy)

        if instance_state == "TERMINATING":
            logging.info(f'Instance_State: {instance_state}')
            logging.info("Instance successfully terminated.\n")
            sys.exit(0)
        else:
            logging.error("Instance termination failed.\n")
            sys.exit(1)
    else:
        logging.error("Failed to fetch instance metadata.\n")
        sys.exit(1)

if __name__ == "__main__":
    main()