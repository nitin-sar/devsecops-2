# dev-radar
Application based on Omnistack 10 

- The main technologies used are : Nodejs , React and React Native
- This repository covers backend only. 
  <br> For the frontend part please access - [dev-radar-frontend](https://github.com/mgiatti/dev-radar-frontend)
  <br> For the mobile part please access - [dev-radar-mobile](https://github.com/mgiatti/dev-radar-mobile)

# important
to get things work you should create a .env file in the root of your project with the following parameters:

- DB_ADMIN_USERNAME - database user name
- DB_ADMIN_PASSWORD - database admin password
- DB_NAME - database name
- DB_HOST - database host
- DB_PORT - database port (not used in URI connection)
- DB_PREFIX - database prefix
- GITHUB_API - github api url - default https://api.github.com
- LISTEN_PORT - port to be listen to the webservice

For more info please check dotenv - https://www.npmjs.com/package/dotenv

## DevSecOps pipeline

GitHub Actions runs on pushes and pull requests targeting `main`. It installs the
locked dependencies, runs an npm audit and tests, performs SonarQube analysis and
Quality Gate validation, builds the container, and scans it with Trivy. Reports are
retained as artifacts; on protected `main` pushes the Trivy JSON report is encrypted
with AES-256 before it is uploaded and published to Nexus. Only a passing pipeline
publishes a commit-SHA-tagged image to Amazon ECR through AWS OIDC.

### Required GitHub configuration

Repository secrets: `SONAR_TOKEN`, `SONAR_HOST_URL`, `REPORT_ENCRYPTION_KEY`,
`NEXUS_URL`, `NEXUS_USERNAME`, `NEXUS_PASSWORD`, and `AWS_ROLE_TO_ASSUME`.
Repository variables: `NEXUS_REPOSITORY`, `AWS_REGION`, and `ECR_REPOSITORY`.

`REPORT_ENCRYPTION_KEY` must be a high-entropy passphrase. Generate it outside the
repository and never commit it or store it in an environment file. The AWS role must
trust GitHub's OIDC provider and restrict its `sub` claim to
`repo:nitin-sar/devsecops-2:ref:refs/heads/main`.

### Local checks

```bash
yarn install --frozen-lockfile
yarn test
docker build -t dev-radar-backend:local .
```

The container defaults to port `3000`; provide the database and GitHub API
environment variables documented above when running it.
