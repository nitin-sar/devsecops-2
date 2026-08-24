# CI/CD external setup

The workflow is committed in `.github/workflows/devsecops.yml`. Configure the
following GitHub repository secrets (Settings > Secrets and variables > Actions):

| Secret | Value |
| --- | --- |
| `SONAR_TOKEN` | Token for the configured SonarQube project |
| `SONAR_HOST_URL` | Reachable SonarQube Server URL, such as `https://sonar.example.com` |
| `REPORT_ENCRYPTION_KEY` | Long random passphrase used only for AES-256 report encryption |
| `NEXUS_URL` | Nexus base URL, without the repository path |
| `NEXUS_USERNAME` | Least-privilege Nexus upload account |
| `NEXUS_PASSWORD` | Password or token for that account |
| `AWS_ROLE_TO_ASSUME` | IAM role ARN trusted by GitHub Actions OIDC |

Set the repository variables `NEXUS_REPOSITORY`, `AWS_REGION`, and
`ECR_REPOSITORY`. The ECR repository must already exist.

## SonarQube

Create a SonarQube project with key `nitin-sar_devsecops-2`, apply the desired
Quality Gate, and ensure the SonarQube Server URL is reachable from GitHub-hosted
runners. A private, local-only SonarQube instance cannot be reached by them.

## Nexus

Create a hosted raw repository named by `NEXUS_REPOSITORY`. Grant the Nexus account
only browse and add/edit rights for that repository. The workflow uploads the
encrypted Trivy report to:

`<NEXUS_URL>/repository/<NEXUS_REPOSITORY>/dev-radar-backend/<commit-sha>/trivy-image.json.enc`

## AWS OIDC and ECR

Add `token.actions.githubusercontent.com` as an IAM OIDC provider with audience
`sts.amazonaws.com`. The role in `AWS_ROLE_TO_ASSUME` needs a trust relationship
restricted to this repository's `main` branch:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Federated": "arn:aws:iam::<ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com"},
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {"token.actions.githubusercontent.com:aud": "sts.amazonaws.com"},
      "StringLike": {"token.actions.githubusercontent.com:sub": "repo:nitin-sar/devsecops-2:ref:refs/heads/main"}
    }
  }]
}
```

Attach a least-privilege policy allowing ECR authentication and image upload only
to the target ECR repository. Do not add long-lived AWS access keys as GitHub
secrets.

## Repository protection

Protect `main`, require the `Verify, analyze, and scan` check before merging, and
restrict direct pushes as appropriate for the team. The publish job runs only for a
successful direct push to `main`; it does not run for pull requests.
