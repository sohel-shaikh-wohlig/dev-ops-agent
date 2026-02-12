export const CLIENTS = [
  { key: "vaultfy", value: "Vaultfy" },
] as const;

export const RESOURCE_TYPES = [
  { key: "gcs", value: "GCS Bucket" },
  { key: "svc", value: "Service Account" },
] as const;

export const BUCKET_VISIBILITY = [
  { key: "private", value: "Private" },
  { key: "public-read", value: "Public Read" },
] as const;
