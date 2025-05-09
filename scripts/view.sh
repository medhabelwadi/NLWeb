#!/usr/bin/env bash
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
REPO_DIR=$SCRIPT_DIR/../

# includes
source "$SCRIPT_DIR/lib/shell_logger.sh"
source "$SCRIPT_DIR/lib/az.sh"
source "$SCRIPT_DIR/lib/state.sh"

function main(){
    load_deployment_state
    _info "\nAzure AI Foundry: $FOUNDRY_URL"
}

# invoke main last to ensure all functions and variables are defined
main