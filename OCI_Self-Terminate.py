# coding: utf-8

# - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Name: OCI_Self-Terminate.py
#
# Author: Florian Bonneville
# Version: 1.0.1 - Oct. 16, 2024
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
# Instance prerequisites:
# python3 -m pip install pip -U --user
# python3 -m pip install wheel oci requests -U --user
# 
# Usage:
# python3 ./OCI_Self-Terminate.py
# 
# Disclaimer: 
# This script is an independent tool developed by 
# Florian Bonneville and is not affiliated with or 
# supported by Oracle. It is provided as-is and without 
# any warranty or official endorsement from Oracle
# - - - - - - - - - - - - - - - - - - - - - - - - - - - -

version="1.0.1"

import sys
import oci
import requests
import logging
from datetime import datetime

def print_log_content(log_file):

    print("\nLog file content:\n")
    try:
        with open(log_file, 'r') as f:
            print(f.read())
    except FileNotFoundError:
        print(f"Error: The file '{log_file}' does not exist.")
    except Exception as e:
        print(f"An error occurred: {e}")

def get_instance_metadata(log_file):

    url = "http://169.254.169.254/opc/v2/instance/"
    headers = {"Authorization": "Bearer Oracle"}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.RequestException as e:
        logging.error(f"Failed to fetch instance metadata: {e}")
        print_log_content(log_file)
        sys.exit(1)

    return response.json()

def log_instance_details(data):

    logging.info(f'Instance_Region: {data["canonicalRegionName"]}')
    logging.info(f'Instance_AD: {data["availabilityDomain"]}')
    logging.info(f'Instance_FD: {data["faultDomain"]}')
    logging.info(f'Instance_Name: {data["displayName"]}')
    logging.info(f'Instance_ID: {data["id"]}')
    logging.info(f'Instance_Shape: {data["shape"]}')

def terminate_instance(core_client, instance_id, custom_retry_strategy, log_file):

    try:
        core_client.terminate_instance(
            instance_id=instance_id,
            preserve_boot_volume=False, # /!\ 'False' terminates the Boot Volume otherwise use 'True'
            preserve_data_volumes_created_at_launch=False, # /!\ 'False' terminates the attached Block Volumes created during instance launch otherwise use 'True'
            retry_strategy=custom_retry_strategy)
        
        logging.info(f'Instance termination requested')
        return

    except Exception as e:
        logging.error(f"Failed to terminate instance: {e}")
        print_log_content(log_file)
        sys.exit(1)

def main():
    
    # set log file in ./migration_YYYY-MM-DD_HH-mm.log for debugging
    now=datetime.now().strftime("%Y-%m-%d_%H-%M")
    log_file=f'inst_termination{now}.log'

    logging.basicConfig(
        filename=log_file,
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
        )
    
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

    logging.info("Fetching instance metadata...")
    instance_data = get_instance_metadata(log_file)

    if instance_data:
        log_instance_details(instance_data)
        instance_id = instance_data.get("id")
        if not instance_id:
            logging.error("Instance ID not found in metadata.\n")
            print_log_content(log_file)
            sys.exit(1)

        core_client = oci.core.ComputeClient(config=config, signer=signer)

        logging.info("Starting instance termination...")
        terminate_instance(core_client, instance_id, custom_retry_strategy, log_file)
        
        try:
            wait_termination = oci.wait_until(
                core_client,
                core_client.get_instance(instance_id),
                'lifecycle_state',
                'TERMINATING',
                max_wait_seconds=600
            )
            if wait_termination.data.lifecycle_state == "TERMINATING":
                logging.info(f'Instance_State: {wait_termination.data.lifecycle_state}')
                print_log_content(log_file)
                sys.exit(0)

        except Exception as e:
            required_attributes = ["target_service", "status", "code", "message", "operation_name"]
            if all(hasattr(e, attr) for attr in required_attributes):
                 if (e.target_service == "compute" and e.status == 404 and e.code == "NotAuthorizedOrNotFound" and "not found" in e.message and e.operation_name == "get_instance"):
                    logging.info("Instance termination succeeded")
                    print_log_content(log_file)
                    sys.exit(0)
            else:
                logging.error(f"Instance Termination failed: {e}")
                print_log_content(log_file)
                sys.exit(1)
    else:
        logging.error("Failed to fetch instance metadata.")
        print_log_content(log_file)
        sys.exit(1)

if __name__ == "__main__":
    main()