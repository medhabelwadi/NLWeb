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
