#!/usr/bin/env bash

declare AZ_CLI_INSTALL_DOCS="https://learn.microsoft.com/cli/azure/install-azure-cli"

function check_az_cli_logged_in(){
    if ! az account show &> /dev/null
    then
        _error "You are not logged in to Azure CLI. Please log in using 'az login'."
        exit 1
    fi

}

function check_az_cli_installed(){
    if ! command -v az &> /dev/null
    then
        _error "Azure CLI is not installed and is a required dependency.\n$AZ_CLI_INSTALL_DOCS"
        exit 1
    fi
}

function set_subscription_id(){
    subscription_id=$(az account list --query "[?isDefault].id" -o tsv)
    if [ -z "$subscription_id" ]; then
        _error "No default subscription found. Please set a default subscription using 'az account set --subscription <subscription_name_or_id>'."
        exit 1
    fi
}

function set_tenant_id(){
    tenant_id=$(az account list --query "[?isDefault].tenantId" -o tsv)
    if [ -z "$tenant_id" ]; then
        _error "No default tenant found. Please set a default tenant using 'az account set --subscription <subscription_name_or_id>'."
        exit 1
    fi
}

function fetch_secret_from_keyvault() {
    local secret_name="$1"
    local export_name="$2"
    local keyvault_name="${AZURE_KEYVAULT_NAME}"
    local resource_group="${AZURE_KEYVAULT_RESOURCE_GROUP}"
    
    if [ -z "$keyvault_name" ] || [ -z "$resource_group" ] || [ -z "$secret_name" ]; then
        _error "Error: Missing required variables for Key Vault access."
        _error "Required variables:"
        _error "  AZURE_KEYVAULT_NAME: ${keyvault_name:-Not set}"
        _error "  AZURE_KEYVAULT_RESOURCE_GROUP: ${resource_group:-Not set}"
        _error"  Secret Name: ${secret_name:-Not set}"
        return 1
    fi
    
    _debug "> Fetching secret '$secret_name' from Key Vault '$keyvault_name' in resource group '$resource_group'"
    
    # Ensure we're logged in and have access to the Key Vault
    if ! az keyvault show --name "$keyvault_name" --resource-group "$resource_group" > /dev/null 2>&1; then
        _error "Error: Could not access Key Vault. Please check your permissions and resource names."
        return 1
    fi
    
    # Fetch the secret value
    local secret_value
    secret_value=$(az keyvault secret show --vault-name "$keyvault_name" --name "$secret_name" --query "value" -o tsv)
    _debug "> Secret value: $secret_value"
    if [ -z "$secret_value" ]; then
        _error "Error: Failed to retrieve secret or secret is empty."
        return 1
    fi
    
    _debug "> Successfully retrieved secret '$secret_name'"

    eval "export $export_name=\"$secret_value\""
    return 0
}