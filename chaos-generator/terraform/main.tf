terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
  }
}

provider "google" {
  project     = var.project_id
  region      = var.region
  credentials = file("/home/lostborion/.gcp/heimr-agent-sa.json")
}

# GKE Cluster
resource "google_container_cluster" "primary" {
  name     = var.cluster_name
  location = var.zone
  
  # We can't create a cluster with no node pool defined, but we want to manage the node pool separately usually.
  # However, for simplicity and matching the "default-pool" usually created:
  remove_default_node_pool = true
  initial_node_count       = 1

  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  release_channel {
    channel = "REGULAR"
  }

  monitoring_config {
    managed_prometheus {
      enabled = true
    }
  }
}

resource "google_container_node_pool" "primary_nodes" {
  name       = "default-pool"
  location   = var.zone
  cluster    = google_container_cluster.primary.name
  node_count = 3

  node_config {
    machine_type = "e2-standard-4"
    disk_size_gb = 50
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]
  }
}

# Artifact Registry
resource "google_artifact_registry_repository" "repo" {
  location      = var.region
  repository_id = var.repo_name
  description   = "Heimr.ai Simulation Images"
  format        = "DOCKER"
}

# GCS Bucket
resource "google_storage_bucket" "data_bucket" {
  name          = var.bucket_name
  location      = var.bucket_location
  force_destroy = true

  uniform_bucket_level_access = true
}
