export const CLIENTS = [
  { key: "vaultfy", value: "Vaultfy" },
] as const;

export const RESOURCE_TYPES = [
  { key: "gcs", value: "GCS Bucket" },
  { key: "svc", value: "Service Account" },
  { key: "vm", value: "Virtual Machine" },
] as const;

export const BUCKET_VISIBILITY = [
  { key: "private", value: "Private" },
  { key: "public-read", value: "Public Read" },
] as const;

export const SERVICE_ACCOUNT_ROLES = [
  { key: "roles/compute.admin", value: "Compute Admin" },
  { key: "roles/storage.objectAdmin", value: "Storage Object Admin" },
] as const;

export const GCP_MACHINE_TYPE = [
  { key: "e2-standard-2", value: "e2-standard-2" },
  { key: "e2-small", value: "e2-small" },
  { key: "n2d-standard-2", value: "n2d-standard-2" },
] as const

export const GCP_DISK_TYPE = [
  { key: "pd-standard", value: "pd-standard" },
  { key: "pd-balanced", value: "pd-balanced" },
  { key: "pd-ssd", value: "pd-ssd" },
] as const

export const GCP_IMAGE = [
  { key: "projects/ubuntu-os-cloud/global/images/ubuntu-minimal-2404-noble-amd64-v20250722", value: "Ubuntu 24" },
  { key: "ubuntu-2204-focal-v20220622", value: "Ubuntu 22.04" },
] as const