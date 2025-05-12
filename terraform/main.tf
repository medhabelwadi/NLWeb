# Get current Azure client configuration
data "azurerm_client_config" "current" {}

# Generate random string for resource names
resource "random_string" "prefix" {
  count   = var.prefix == "" ? 1 : 0
  length  = 6
  special = false
  upper   = false
}

# Resource group
resource "azurerm_resource_group" "main" {
  name     = local.resource_group_name
  location = var.resource_group_location
}

# Environment file template
resource "local_file" "env_file_template" {
  count    = fileexists(local.env_template_path) ? 0 : 1
  content  = <<-EOT
# Key Vault Settings
AZURE_KEYVAULT_NAME="${var.keyvault_name}"
AZURE_KEYVAULT_RESOURCE_GROUP="${var.keyvault_resource_group}"
SEARCH_ENDPOINT_SECRET_NAME="${var.search_endpoint_secret_name}"
SEARCH_API_KEY_SECRET_NAME="${var.search_api_key_secret_name}"

# Azure OpenAI Settings
AZURE_OPENAI_API_KEY="<to be filled by terraform>"
AZURE_OPENAI_ENDPOINT="<to be filled by terraform>"

# Azure Vector Search Settings
AZURE_VECTOR_SEARCH_API_KEY="<to be filled by terraform>"
AZURE_VECTOR_SEARCH_ENDPOINT="<to be filled by terraform>"
EOT
  filename = local.env_template_path
}
