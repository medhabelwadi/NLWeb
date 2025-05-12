variable "prefix" {
  description = "Prefix for all resources"
  type        = string
  default     = ""
}

variable "location" {
  description = "The Azure location where resources should be created"
  type        = string
  default     = "eastus2"
}

variable "resource_group_location" {
  description = "The Azure location for the resource group"
  type        = string
  default     = "eastus"
}

variable "openai_sku" {
  description = "SKU for OpenAI resource"
  type        = string
  default     = "S0"
}

variable "openai_model_sku_capacity" {
  description = "Capacity for OpenAI model"
  type        = number
  default     = 1
}

variable "openai_model_sku_name" {
  description = "SKU name for OpenAI model"
  type        = string
  default     = "GlobalStandard"
}

variable "openai_models" {
  description = "Map of OpenAI models to deploy"
  type = map(object({
    name    = string
    version = string
  }))
  default = {
    "gpt-4.1" = {
      name    = "gpt-4.1"
      version = "2025-04-14"
    },
    "gpt-4.1-mini" = {
      name    = "gpt-4.1-mini"
      version = "2025-04-14"
    },
    "text-embedding-3-small" = {
      name    = "text-embedding-3-small"
      version = "1"
    }
  }
}

variable "web_app_location" {
  description = "Location for web app resources"
  type        = string
  default     = "westus"
}

variable "app_service_sku" {
  description = "SKU for App Service Plan"
  type        = string
  default     = "P1v3"
}

variable "acr_sku" {
  description = "SKU for Azure Container Registry"
  type        = string
  default     = "Standard"
}

variable "keyvault_name" {
  description = "Name of the existing Key Vault"
  type        = string
}

variable "keyvault_resource_group" {
  description = "Resource group of the existing Key Vault"
  type        = string
}

variable "search_endpoint_secret_name" {
  description = "Name of the Vector Search endpoint secret in Key Vault"
  type        = string
}

variable "search_api_key_secret_name" {
  description = "Name of the Vector Search API key secret in Key Vault"
  type        = string
}

variable "container_image" {
  description = "Container image for the web app"
  type        = string
  default     = "nlweb"
}

variable "container_tag" {
  description = "Container tag for the web app"
  type        = string
  default     = "latest"
}

variable "save_state_locally" {
  description = "Whether to save deployment state to local .deployment file"
  type        = bool
  default     = true
}
