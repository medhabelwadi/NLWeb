#!/usr/bin/env bash

declare TERRAFORM_CLI_INSTALL_DOCS="https://developer.hashicorp.com/terraform/install"

function check_terraform_cli_installed(){
    if ! command -v tf2 &> /dev/null
    then
        _error "Terraform cli is not installed and is a required dependency.\n$TERRAFORM_CLI_INSTALL_DOCS"
        exit 1
    fi
}