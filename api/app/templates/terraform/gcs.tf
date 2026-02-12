terraform {
  backend "gcs" {
    bucket = "{{client}}-terraform-bucket"
    prefix = "/resources/bucket/{{environment}}"
  }
}

module "cloud-storage" {
  source = "../../../modules/gcs_module"
  gcs_bucket = [
    {
      names                    = ["{{bucket_name}}"]
      project_id               = "{{project_id}}"
      location                 = "{{project_location}}"
      storage_class            = "STANDARD"
      public_access_prevention = "enforced"
      labels = {
        access = "private"
      }
    }
  ]
}
