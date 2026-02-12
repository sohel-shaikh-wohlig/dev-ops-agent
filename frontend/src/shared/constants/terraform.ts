export const CLIENTS = [
  { key: "vaultfy", value: "Vaultfy" },
  { key: "client-b", value: "Client B" },
  { key: "client-c", value: "Client C" },
] as const;

export const RESOURCE_TYPES = [
  { key: "ec2", value: "EC2 Instance" },
  { key: "s3_bucket", value: "S3 Bucket" },
  { key: "rds", value: "RDS Database" },
] as const;

export const BUCKET_VISIBILITY = [
  { key: "private", value: "Private" },
  { key: "public-read", value: "Public Read" },
] as const;
