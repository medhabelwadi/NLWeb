# Usage

- Ensure that the az cli is logged into the desired target subscription via `az login`
- Set up the subscription id as an environment variable `export ARM_SUBSCRIPTION_ID=$(az account show --query id -o tsv)`

```conf
keyvault_name = "your-keyvault-name"
keyvault_resource_group = "your-keyvault-rg"
search_endpoint_secret_name = "vector-search-endpoint"
search_api_key_secret_name = "vector-search-api-key"
subscription_id = "your-subscription-id"
tenant_id = "your-tenant-id" # Optional
# Example override in terraform.tfvars
openai_models = {
  "gpt-4.2" = {
    name    = "gpt-4.2"
    version = "2025-08-01"
  },
  "text-embedding-4" = {
    name    = "text-embedding-4"
    version = "1"
  }
}
```

  ```conf
  keyvault_name = "your-keyvault-name"
  keyvault_resource_group = "your-keyvault-rg"
  search_endpoint_secret_name = "vector-search-endpoint"
  search_api_key_secret_name = "vector-search-api-key"
  ```


```bash
cd terraform
terraform init

# Create and save the execution plan
terraform plan -out=tfplan

# Review the plan output carefully before proceeding

# Apply the exact plan you reviewed
terraform apply tfplan
```

## Post installation

```bash
docker build -t nlweb:latest .
az acr login -n <acr>
docker tag nlweb:latest <acr>.azurecr.io/nlweb:latest
docker push <acr>.azurecr.io/nlweb:latest
```

# The below should be automated
- Log into the ACR and ensure the image is there
- Log into the App service: Deployment -> Deployment Center
  - Ensure Continuous deployment is "On"
  - Save