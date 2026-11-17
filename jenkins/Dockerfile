FROM jenkins/jenkins:lts
USER root

# Install Python 3, venv, pip, curl, git, jq
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv git curl jq ca-certificates gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Docker CLI and Docker Compose plugin
RUN install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    && chmod a+r /etc/apt/keyrings/docker.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(. /etc/os-release && echo $VERSION_CODENAME) stable" > /etc/apt/sources.list.d/docker.list \
    && apt-get update && apt-get install -y --no-install-recommends docker-ce-cli docker-compose-plugin \
    && rm -rf /var/lib/apt/lists/*

# Copy Terraform
COPY terraform /usr/local/bin/terraform
RUN chmod +x /usr/local/bin/terraform

# Install required Python test libraries
RUN python3 -m pip install --no-cache-dir --break-system-packages pytest polars sqlalchemy psycopg2-binary anyio

# Grant jenkins user access to docker
RUN usermod -aG root jenkins

USER jenkins

# Pre-install Jenkins pipeline plugins
RUN jenkins-plugin-cli --plugins "workflow-aggregator:latest" "git:latest" "junit:latest"
