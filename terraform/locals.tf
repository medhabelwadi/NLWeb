locals {
  random_prefix        = var.prefix != "" ? var.prefix : random_string.prefix[0].result
  resource_group_name  = "nlweb-rg-${local.random_prefix}"
  openai_resource_name = "nlweb-oai-${local.random_prefix}"
  acr_name             = "nlwebarc${local.random_prefix}"
  app_service_name     = "nlweb-appsvc-${local.random_prefix}"
  web_app_name         = "nlweb-web-${local.random_prefix}"

  foundry_url = "https://ai.azure.com/resource/deployments?wsid=/subscriptions/${data.azurerm_client_config.current.subscription_id}/resourceGroups/${azurerm_resource_group.main.name}/providers/Microsoft.CognitiveServices/accounts/${azurerm_cognitive_account.openai.name}&tid=${data.azurerm_client_config.current.tenant_id}"

  env_file_path        = "${path.root}/../code/.env"
  env_template_path    = "${path.root}/templates/env.tftpl"
  deployment_file_path = "${path.root}/.deployment"
}