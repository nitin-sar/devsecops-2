#!/usr/bin/env python3

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from datetime import datetime


# ============================================================
# CONFIGURATION
# ============================================================

REPO = Path.cwd()

WORKFLOW = REPO / ".github" / "workflows" / "devsecops.yml"
SONAR = REPO / "sonar-project.properties"

BACKUP_DIR = REPO / ".devsecops-backup"


WORKFLOW_CONTENT = r'''name: DevSecOps Pipeline

on:
  push:
    branches:
      - main
      - master

  pull_request:
    branches:
      - main
      - master

permissions:
  contents: read

env:
  NODE_VERSION: "20"
  IMAGE_NAME: dev-radar-backend

  # AWS
  AWS_REGION: us-east-1
  ECR_REGISTRY: public.ecr.aws/u1g0y0f1
  ECR_REPOSITORY: 3-tier

  # Nexus
  NEXUS_REPOSITORY: trivy-reports


# ============================================================
# JOB 1
# VERIFY + ANALYZE + SCAN
# ============================================================

jobs:

  verify-analyze-scan:

    name: Verify, analyze, and scan

    runs-on: ubuntu-latest

    steps:

      # ========================================================
      # 1. CHECKOUT
      # ========================================================

      - name: Checkout source
        uses: actions/checkout@v4


      # ========================================================
      # 2. SETUP NODE
      # ========================================================

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: npm


      # ========================================================
      # 3. INSTALL YARN
      # ========================================================

      - name: Setup Yarn
        run: |
          npm install -g yarn
          yarn --version


      # ========================================================
      # 4. INSTALL DEPENDENCIES
      # ========================================================

      - name: Install dependencies
        run: yarn install --frozen-lockfile


      # ========================================================
      # 5. RUN TESTS
      # ========================================================

      - name: Run tests
        run: npm test -- --runInBand


      # ========================================================
      # 6. SONARQUBE
      # ========================================================
      #
      # Disabled until SonarQube secrets are configured.
      #
      # ========================================================

      - name: SonarQube Scan
        if: ${{ false }}
        uses: SonarSource/sonarqube-scan-action@v6
        env:
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
          SONAR_HOST_URL: ${{ secrets.SONAR_HOST_URL }}


      # ========================================================
      # 7. BUILD DOCKER IMAGE
      # ========================================================

      - name: Build Docker image
        run: |
          docker build \
            -t $IMAGE_NAME:${GITHUB_SHA} \
            -t $IMAGE_NAME:latest \
            .


      # ========================================================
      # 8. INSTALL TRIVY
      # ========================================================

      - name: Install Trivy
        run: |

          sudo apt-get update

          sudo apt-get install -y \
            wget \
            apt-transport-https \
            gnupg \
            lsb-release

          wget -qO - \
            https://aquasecurity.github.io/trivy-repo/deb/public.key \
            | gpg --dearmor \
            | sudo tee /usr/share/keyrings/trivy.gpg > /dev/null

          echo "deb [signed-by=/usr/share/keyrings/trivy.gpg] \
            https://aquasecurity.github.io/trivy-repo/deb \
            $(lsb_release -sc) main" \
            | sudo tee /etc/apt/sources.list.d/trivy.list

          sudo apt-get update

          sudo apt-get install -y trivy

          trivy --version


      # ========================================================
      # 9. TRIVY IMAGE SCAN
      # ========================================================

      - name: Scan Docker image with Trivy
        run: |

          mkdir -p reports

          trivy image \
            --format json \
            --output reports/trivy-image.json \
            $IMAGE_NAME:${GITHUB_SHA}


      # ========================================================
      # 10. DISPLAY TRIVY SUMMARY
      # ========================================================

      - name: Display Trivy scan summary
        run: |

          trivy image \
            --severity HIGH,CRITICAL \
            $IMAGE_NAME:${GITHUB_SHA}


      # ========================================================
      # 11. UPLOAD TRIVY REPORT AS ARTIFACT
      # ========================================================

      - name: Upload Trivy report
        uses: actions/upload-artifact@v4
        with:
          name: trivy-report-${{ github.sha }}
          path: reports/trivy-image.json


      # ========================================================
      # 12. ENCRYPT TRIVY REPORT
      # ========================================================

      - name: Encrypt Trivy report
        env:
          TRIVY_REPORT_ENCRYPTION_KEY: ${{ secrets.TRIVY_REPORT_ENCRYPTION_KEY }}

        run: |

          set -e

          echo "Checking encryption key..."

          test -n "$TRIVY_REPORT_ENCRYPTION_KEY"

          echo "Encrypting Trivy report..."

          openssl enc \
            -aes-256-cbc \
            -pbkdf2 \
            -salt \
            -in reports/trivy-image.json \
            -out reports/trivy-image.json.enc \
            -pass env:TRIVY_REPORT_ENCRYPTION_KEY

          echo "Encrypted report created."

          ls -lh reports/


      # ========================================================
      # 13. UPLOAD ENCRYPTED REPORT TO NEXUS
      # ========================================================

      - name: Upload encrypted report to Nexus
        env:
          NEXUS_URL: ${{ secrets.NEXUS_URL }}
          NEXUS_USERNAME: ${{ secrets.NEXUS_USERNAME }}
          NEXUS_PASSWORD: ${{ secrets.NEXUS_PASSWORD }}
          NEXUS_REPOSITORY: ${{ env.NEXUS_REPOSITORY }}

        run: |

          set -e

          echo "Checking Nexus configuration..."

          test -n "$NEXUS_URL"
          test -n "$NEXUS_USERNAME"
          test -n "$NEXUS_PASSWORD"
          test -n "$NEXUS_REPOSITORY"

          echo "Nexus URL configured."
          echo "Nexus repository: $NEXUS_REPOSITORY"

          echo "Testing Nexus connectivity..."

          curl \
            --fail \
            --silent \
            --show-error \
            --connect-timeout 10 \
            "$NEXUS_URL/service/rest/v1/status"

          echo "Nexus connectivity successful."

          echo "Uploading encrypted Trivy report..."

          curl \
            --fail \
            --silent \
            --show-error \
            --user "$NEXUS_USERNAME:$NEXUS_PASSWORD" \
            --upload-file reports/trivy-image.json.enc \
            "${NEXUS_URL%/}/repository/${NEXUS_REPOSITORY}/${IMAGE_NAME}/${GITHUB_SHA}/trivy-image.json.enc"

          echo "Encrypted Trivy report uploaded successfully."


# ============================================================
# JOB 2
# PUBLISH APPROVED IMAGE
# ============================================================

  publish:

    name: Publish approved image

    runs-on: ubuntu-latest

    needs:
      - verify-analyze-scan

    steps:

      # ========================================================
      # 1. CHECKOUT
      # ========================================================

      - name: Checkout source
        uses: actions/checkout@v4


      # ========================================================
      # 2. CONFIGURE AWS CREDENTIALS
      # ========================================================

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}


      # ========================================================
      # 3. VERIFY AWS ACCESS
      # ========================================================

      - name: Verify AWS identity
        run: |
          aws sts get-caller-identity


      # ========================================================
      # 4. LOGIN TO AMAZON ECR PUBLIC
      # ========================================================

      - name: Login to Amazon ECR Public
        run: |

          aws ecr-public get-login-password \
            --region $AWS_REGION \
            | docker login \
            --username AWS \
            --password-stdin public.ecr.aws


      # ========================================================
      # 5. BUILD DOCKER IMAGE
      # ========================================================

      - name: Build Docker image
        run: |

          docker build \
            -t $ECR_REGISTRY/$ECR_REPOSITORY:$GITHUB_SHA \
            -t $ECR_REGISTRY/$ECR_REPOSITORY:latest \
            .


      # ========================================================
      # 6. PUSH IMAGE WITH COMMIT SHA
      # ========================================================

      - name: Push image to ECR
        run: |

          docker push \
            $ECR_REGISTRY/$ECR_REPOSITORY:$GITHUB_SHA


      # ========================================================
      # 7. PUSH LATEST IMAGE
      # ========================================================

      - name: Push latest image to ECR
        run: |

          docker push \
            $ECR_REGISTRY/$ECR_REPOSITORY:latest


      # ========================================================
      # 8. VERIFY PUBLISHED IMAGE
      # ========================================================

      - name: Verify published image
        run: |

          echo "Image successfully published:"
          echo "$ECR_REGISTRY/$ECR_REPOSITORY:$GITHUB_SHA"

          echo "Latest image:"
          echo "$ECR_REGISTRY/$ECR_REPOSITORY:latest"
'''


SONAR_CONTENT = """sonar.projectKey=devsecops-2
sonar.projectName=devsecops-2
sonar.sources=src
sonar.tests=tests
sonar.test.inclusions=tests/**/*.test.js
sonar.javascript.lcov.reportPaths=coverage/lcov.info
sonar.sourceEncoding=UTF-8
sonar.host.url=http://43.204.150.250:9000
"""


# ============================================================
# HELPERS
# ============================================================

def run(command, check=True):
    print(f"\n$ {' '.join(command)}")

    result = subprocess.run(
        command,
        cwd=REPO,
        text=True,
        capture_output=True
    )

    if result.stdout:
        print(result.stdout.strip())

    if result.stderr:
        print(result.stderr.strip())

    if check and result.returncode != 0:
        raise RuntimeError(
            f"Command failed with exit code {result.returncode}"
        )

    return result


def backup_file(path):
    if not path.exists():
        return

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = BACKUP_DIR / f"{path.name}.{timestamp}.bak"

    shutil.copy2(path, backup)

    print(f"Backup created: {backup}")


def check_git_status():
    result = run(
        ["git", "status", "--porcelain"],
        check=True
    )

    return result.stdout.strip()


def ensure_repo():
    if not (REPO / ".git").exists():
        raise RuntimeError(
            f"{REPO} does not appear to be a Git repository."
        )


# ============================================================
# YAML VALIDATION
# ============================================================

def validate_yaml():
    print("\n========================================")
    print("VALIDATING GITHUB ACTIONS YAML")
    print("========================================")

    try:
        import yaml
    except ImportError:
        print(
            "\nPyYAML is not installed.\n"
            "Install it with:\n"
            "    python3 -m pip install pyyaml\n"
        )
        return False

    try:
        with open(WORKFLOW, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            raise ValueError("Workflow root is not a YAML object.")

        if "jobs" not in data:
            raise ValueError("Missing 'jobs' section.")

        print("YAML syntax: OK")
        print("GitHub Actions 'jobs' section: OK")

        return True

    except Exception as exc:
        print(f"YAML validation FAILED: {exc}")
        return False


# ============================================================
# MODIFY FILES
# ============================================================

def write_files(force=False):
    print("\n========================================")
    print("CHECKING LOCAL CHANGES")
    print("========================================")

    status = check_git_status()

    if status and not force:
        print("\nExisting Git changes detected:")
        print(status)

        raise RuntimeError(
            "\nThere are existing local changes.\n"
            "For safety, the script stopped.\n\n"
            "If you are sure you want to overwrite the workflow "
            "and Sonar configuration, rerun with:\n"
            "    --force\n"
        )

    print("\nCreating backups...")

    backup_file(WORKFLOW)
    backup_file(SONAR)

    WORKFLOW.parent.mkdir(parents=True, exist_ok=True)

    print("\nWriting DevSecOps workflow...")

    WORKFLOW.write_text(
        WORKFLOW_CONTENT,
        encoding="utf-8"
    )

    print(f"Updated: {WORKFLOW}")

    print("\nWriting SonarQube configuration...")

    SONAR.write_text(
        SONAR_CONTENT,
        encoding="utf-8"
    )

    print(f"Updated: {SONAR}")


# ============================================================
# GIT
# ============================================================

def git_diff_check():
    print("\n========================================")
    print("GIT DIFF CHECK")
    print("========================================")

    run(["git", "diff", "--check"])


def git_status():
    print("\n========================================")
    print("FINAL GIT STATUS")
    print("========================================")

    run(["git", "status"])


def commit_changes(message):
    print("\n========================================")
    print("COMMITTING CHANGES")
    print("========================================")

    run([
        "git",
        "add",
        ".github/workflows/devsecops.yml",
        "sonar-project.properties"
    ])

    run([
        "git",
        "commit",
        "-m",
        message
    ])


def sync_and_push():
    print("\n========================================")
    print("SYNCING WITH ORIGIN/MAIN")
    print("========================================")

    run(["git", "fetch", "origin"])

    # Rebase local commits on top of origin/main.
    run(["git", "rebase", "origin/main"])

    print("\n========================================")
    print("PUSHING TO ORIGIN/MAIN")
    print("========================================")

    run(["git", "push", "origin", "main"])


# ============================================================
# MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description="Automate DevSecOps workflow configuration."
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow overwriting existing local changes."
    )

    parser.add_argument(
        "--commit",
        action="store_true",
        help="Commit the generated configuration."
    )

    parser.add_argument(
        "--push",
        action="store_true",
        help="Commit and push changes to origin/main."
    )

    parser.add_argument(
        "--message",
        default="Fix DevSecOps pipeline configuration",
        help="Git commit message."
    )

    args = parser.parse_args()

    if args.push:
        args.commit = True

    try:

        print("\n========================================")
        print("DEVSECOPS AUTOMATION")
        print("========================================")

        print(f"\nRepository: {REPO}")

        ensure_repo()

        # --------------------------------------------
        # WRITE CONFIGURATION
        # --------------------------------------------

        write_files(force=args.force)

        # --------------------------------------------
        # VALIDATE
        # --------------------------------------------

        git_diff_check()

        if not validate_yaml():
            raise RuntimeError(
                "Workflow YAML validation failed."
            )

        # --------------------------------------------
        # SHOW STATUS
        # --------------------------------------------

        git_status()

        # --------------------------------------------
        # COMMIT
        # --------------------------------------------

        if args.commit:

            commit_changes(args.message)

            git_status()

        # --------------------------------------------
        # PUSH
        # --------------------------------------------

        if args.push:

            sync_and_push()

            git_status()

        print("\n========================================")
        print("SUCCESS")
        print("========================================")

        print("\nDevSecOps configuration has been fixed.")

        if not args.commit:
            print(
                "\nChanges are NOT committed."
                "\nReview them first."
            )

        if args.commit and not args.push:
            print(
                "\nChanges are committed locally."
                "\nPush manually with:"
                "\n    git push origin main"
            )

        if args.push:
            print(
                "\nChanges have been pushed to origin/main."
            )

    except KeyboardInterrupt:
        print("\n\nOperation cancelled.")
        sys.exit(130)

    except Exception as exc:
        print("\n========================================")
        print("ERROR")
        print("========================================")
        print(exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
