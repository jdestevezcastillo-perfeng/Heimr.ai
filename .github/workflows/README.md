# GitHub Actions for Infrastructure Management

This directory contains GitHub Actions workflows for managing the GCP infrastructure using Terraform.

## Workflows

### 1. Terraform Apply (`terraform-apply.yml`)
Creates the infrastructure defined in the `terraform/` directory.

**Trigger**: Manual (workflow_dispatch)

**Required Input**: Type "apply" to confirm

**What it does**:
- Authenticates to GCP using Workload Identity Federation
- Runs `terraform init` and `terraform plan`
- Applies the infrastructure changes
- Outputs the created resources

### 2. Terraform Destroy (`terraform-destroy.yml`)
Destroys all infrastructure managed by Terraform.

**Trigger**: Manual (workflow_dispatch)

**Required Input**: Type "destroy" to confirm

**What it does**:
- Authenticates to GCP using Workload Identity Federation
- Runs `terraform plan -destroy`
- Destroys all infrastructure
- Confirms deletion

## Setup Required

Before using these workflows, you need to configure the following GitHub secrets:

1. **GCP_WORKLOAD_IDENTITY_PROVIDER**: The full resource name of your Workload Identity Provider
   ```
   projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/POOL_NAME/providers/PROVIDER_NAME
   ```

2. **GCP_SERVICE_ACCOUNT**: The email of the service account to impersonate
   ```
   SERVICE_ACCOUNT_NAME@PROJECT_ID.iam.gserviceaccount.com
   ```

### Setting up Workload Identity Federation

1. Create a Workload Identity Pool:
   ```bash
   gcloud iam workload-identity-pools create "github-pool" \
     --project="PROJECT_ID" \
     --location="global" \
     --display-name="GitHub Actions Pool"
   ```

2. Create a Workload Identity Provider:
   ```bash
   gcloud iam workload-identity-pools providers create-oidc "github-provider" \
     --project="PROJECT_ID" \
     --location="global" \
     --workload-identity-pool="github-pool" \
     --display-name="GitHub Provider" \
     --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
     --issuer-uri="https://token.actions.githubusercontent.com"
   ```

3. Create a Service Account and grant permissions:
   ```bash
   gcloud iam service-accounts create terraform-sa \
     --display-name="Terraform Service Account"
   
   gcloud projects add-iam-policy-binding PROJECT_ID \
     --member="serviceAccount:terraform-sa@PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/editor"
   ```

4. Allow the GitHub repository to impersonate the service account:
   ```bash
   gcloud iam service-accounts add-iam-policy-binding terraform-sa@PROJECT_ID.iam.gserviceaccount.com \
     --project="PROJECT_ID" \
     --role="roles/iam.workloadIdentityUser" \
     --member="principalSet://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/attribute.repository/YOUR_GITHUB_USERNAME/Heimr.ai"
   ```

## Usage

1. Go to the "Actions" tab in your GitHub repository
2. Select either "Terraform Apply" or "Terraform Destroy"
3. Click "Run workflow"
4. Type the required confirmation ("apply" or "destroy")
5. Click "Run workflow" to start

## Security Notes

- Both workflows require manual confirmation to prevent accidental execution
- Uses Workload Identity Federation (no long-lived credentials)
- The service account should have minimal required permissions
- Consider using Terraform Cloud/Enterprise for state management in production
