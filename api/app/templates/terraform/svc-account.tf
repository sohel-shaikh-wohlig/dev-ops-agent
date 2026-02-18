terraform {
  backend "gcs" {
    bucket = "{{client}}-terraform-bucket"
    prefix = "/resources/service-accounts/{{environment}}"
  }
}

module "service_accounts" {
  source = "../../../../modules/service_account_module"

  service_accounts = [
    {
      project_id   = "{{project_id}}"
      name         = "{{svc_name}}"
      display_name = "{{svc_name}}"
      project_roles = ["{{project_id}}=>{{gcp_roles}}"]
      generate_keys = "{{is_generate_keys}}"
    }
  ]
}