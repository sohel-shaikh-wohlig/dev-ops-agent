terraform {
  backend "gcs" {
    bucket = "{{client}}-terraform-bucket"
    prefix = "/resources/vm/{{environment}}"
  }
}

# Reserve a static IP address for VM
resource "google_compute_address" "{{vm_terraform_name}}_ip" {
  name    = "{{vm_name}}-ip"
  project = "{{project_id}}"
  region  = "{{project_location}}"
}

#VM for common VPN in network project
resource "google_compute_instance" "{{vm_terraform_name}}" {
  project = "{{project_id}}"
  boot_disk {
    auto_delete = true
    device_name = "{{vm_name}}"

    initialize_params {
      image = "{{os}}"
      size  = {{disk_size}}
      type  = "{{disk_type}}"
    }

    mode = "READ_WRITE"
  }

  can_ip_forward      = false
  deletion_protection = true
  enable_display      = false
  tags                = ["{{vm_name}}"]
  labels = {
    goog-ec-src   = "vm_add-tf"
    resource_name = "{{vm_name}}"
  }

  machine_type = "{{machine_type}}"
  name         = "{{vm_name}}"

  network_interface {
    access_config {
      nat_ip       = google_compute_address.{{vm_terraform_name}}_ip.address
      network_tier = "PREMIUM"
    }

    queue_count = 0
    stack_type  = "IPV4_ONLY"
    subnetwork  = "{{subnet_name}}"
  }

  scheduling {
    automatic_restart   = true
    on_host_maintenance = "MIGRATE"
    preemptible         = false
    provisioning_model  = "STANDARD"
  }

  service_account {
    email  = "{{gcp_service_account_email}}"
    scopes = ["https://www.googleapis.com/auth/devstorage.read_only", "https://www.googleapis.com/auth/logging.write", "https://www.googleapis.com/auth/monitoring.write", "https://www.googleapis.com/auth/service.management.readonly", "https://www.googleapis.com/auth/servicecontrol", "https://www.googleapis.com/auth/trace.append"]
  }

  shielded_instance_config {
    enable_integrity_monitoring = true
    enable_secure_boot          = true
    enable_vtpm                 = true
  }

  zone = "{{project_location}}-a"
  lifecycle {
    ignore_changes = [
      metadata
    ]
  }
}