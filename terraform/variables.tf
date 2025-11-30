variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "region" {
  description = "The default region for resources"
  type        = string
  default     = "asia-northeast1"
}

variable "zone" {
  description = "The zone for the GKE cluster"
  type        = string
  default     = "us-central1-a"
}

variable "cluster_name" {
  description = "The name of the GKE cluster"
  type        = string
  default     = "heimr-cluster"
}

variable "repo_name" {
  description = "The name of the Artifact Registry repository"
  type        = string
  default     = "heimr"
}

variable "bucket_name" {
  description = "The name of the GCS bucket"
  type        = string
}
