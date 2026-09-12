# Self-Healing CI/CD Pipeline with Jenkins, Docker & Kubernetes

A hands-on DevOps project implementing an automated CI/CD pipeline with **GitHub, Jenkins, Docker, Docker Hub, Kind Kubernetes, Flask, Redis, and Kubernetes self-healing**.

A code change pushed to GitHub automatically triggers Jenkins, which builds and pushes new Docker images and deploys them to Kubernetes. Kubernetes then manages application availability through Deployments, ReplicaSets, rolling updates, and pod recreation.

---

## Architecture

```text
                    Developer
                        │
                        │ git push
                        ▼
                    ┌─────────┐
                    │ GitHub  │
                    └────┬────┘
                         │
                    Webhook
                         │
                         ▼
                 ┌──────────────┐
                 │    ngrok     │
                 │ Public tunnel│
                 └──────┬───────┘
                        │
                        ▼
                 ┌──────────────┐
                 │    Jenkins   │
                 │ Docker       │
                 │ Container    │
                 └──────┬───────┘
                        │
              ┌─────────┴─────────┐
              │                   │
         Docker Socket        kubectl
              │                   │
              ▼                   ▼
       Docker Engine         Kind Cluster
              │                   │
              ▼                   ▼
         Docker Hub        Kubernetes Deployments
                                  │
                         ┌────────┼────────┐
                         │        │        │
                        API     Worker    Redis
```

### CI/CD Flow

```text
Code Change
    ↓
git push
    ↓
GitHub Webhook
    ↓
Jenkins
    ↓
Checkout
    ↓
Build Docker Images
    ↓
Push Images to Docker Hub
    ↓
kubectl set image
    ↓
Kubernetes Rolling Update
    ↓
New Pods
    ↓
Health / Availability maintained by Kubernetes
```

---

# Project Goals

The project demonstrates:

- Docker-based application containerization
- Jenkins-based CI/CD
- GitHub webhook integration
- Docker Hub image publishing
- Kubernetes deployment using Kind
- Kubernetes Services and NodePort
- Kubernetes rolling updates
- Versioned Docker images using Jenkins build numbers
- Kubernetes self-healing
- Jenkins-to-Kubernetes networking
- Docker socket based Docker builds from Jenkins
- Practical troubleshooting of Docker, Kubernetes, networking and CI/CD failures

---

# Technology Stack

| Component | Technology |
|---|---|
| Application | Flask |
| Database/Queue | Redis |
| Worker | Python worker |
| Containerization | Docker |
| Container Registry | Docker Hub |
| CI/CD | Jenkins |
| Source Control | Git + GitHub |
| Webhook Tunnel | ngrok |
| Kubernetes | Kind |
| Kubernetes CLI | kubectl |
| Host | Ubuntu/WSL2 + Docker Desktop |
| Orchestration | Kubernetes Deployments, Services, ReplicaSets |

---

# Application Components

## API

The Flask API exposes application endpoints such as:

```text
GET /version
GET /tasks
POST /tasks
```

The `/version` endpoint is useful for verifying that a newly built image has actually been deployed.

Example:

```json
{
  "message": "Hello from API v1"
}
```

The endpoint can also be extended to expose deployment/build information such as:

```json
{
  "version": "1.3.0",
  "build": "42",
  "hostname": "api-deployment-xxxxx"
}
```

The pod hostname is useful for verifying which Kubernetes pod handled the request.

---

## Worker

The worker processes background tasks using Redis.

Multiple worker replicas can be managed by Kubernetes:

```text
Worker Pod 1 ─┐
Worker Pod 2 ─┼──► Redis
Worker Pod 3 ─┘
```

---

## Redis

Redis acts as the backend used by the API/worker workflow.

It is deployed separately as a Kubernetes workload and accessed through a Kubernetes Service.

---

# Docker

The application components are containerized independently.

Example images:

```text
nitinxyz/poc-api:<tag>
nitinxyz/poc-worker:<tag>
```

Initially, Kubernetes manifests used:

```yaml
image: nitinxyz/poc-api:latest
```

and:

```yaml
image: nitinxyz/poc-worker:latest
```

The CI/CD pipeline later changed the deployed image using the Jenkins build number:

```text
nitinxyz/poc-api:${BUILD_NUMBER}
nitinxyz/poc-worker:${BUILD_NUMBER}
```

This makes each Jenkins build identifiable.

---

# Jenkins

Jenkins runs inside a Docker container.

The Jenkins container is exposed on:

```text
localhost:9090
```

with:

```text
Host 9090 → Container 8080
```

Jenkins is connected to:

```text
default
kind
```

Docker networks.

The `kind` network is important because it allows Jenkins to communicate directly with the Kind Kubernetes control-plane container.

---

# Jenkins Docker Socket

The Jenkins container mounts the host Docker socket:

```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock
```

This allows the Docker CLI inside Jenkins to communicate with the host Docker daemon.

The architecture is:

```text
Jenkins Pipeline
      │
      ▼
Docker CLI
      │
      ▼
/var/run/docker.sock
      │
      ▼
Host Docker Daemon
      │
      ├── build images
      ├── run containers
      └── push images
```

The Docker daemon is **not running inside Jenkins**.

Jenkins only runs the Docker CLI; the actual Docker daemon is provided by the host.

---

# Jenkins Dockerfile

The Jenkins image installs:

- Docker CLI
- curl
- kubectl

It also configures the Jenkins user to access the Docker socket.

Conceptually:

```dockerfile
FROM jenkins/jenkins:lts

USER root

RUN apt-get update && \
    apt-get install -y docker.io curl && \
    apt-get clean

RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"

RUN chmod +x kubectl && \
    mv kubectl /usr/local/bin/

RUN groupmod -g 989 docker && \
    usermod -aG docker jenkins

USER jenkins
```

The Docker group GID was aligned with the host Docker socket group.

---

# Jenkins → Kubernetes Connectivity

The Kind cluster runs as Docker containers.

The Kubernetes API server is exposed inside the Kind network through:

```text
self-healing-cluster-control-plane:6443
```

The host kubeconfig originally contained an endpoint similar to:

```text
https://127.0.0.1:<random-port>
```

That works from the host but not from the Jenkins container.

Inside Jenkins:

```text
127.0.0.1
```

means:

```text
Jenkins container itself
```

not the host and not the Kind control plane.

Therefore Jenkins uses:

```text
https://self-healing-cluster-control-plane:6443
```

because both Jenkins and Kind are attached to the Docker `kind` network.

---

# Jenkins Kubeconfig

The kubeconfig used by Jenkins is stored inside the Jenkins image at:

```text
/usr/local/share/kube/config
```

Jenkins sets:

```groovy
environment {
    KUBECONFIG = "/usr/local/share/kube/config"
}
```

This explicitly tells `kubectl` which configuration file to use.

The final connectivity test was:

```bash
export KUBECONFIG=/usr/local/share/kube/config
kubectl get nodes
```

Result:

```text
NAME                                 STATUS   ROLES           AGE
self-healing-cluster-control-plane   Ready    control-plane   ...
```

This confirmed that Jenkins could successfully communicate with the Kind Kubernetes API server.

---

# Kind Kubernetes Cluster

The local Kubernetes cluster is created using Kind.

Example configuration:

```yaml
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4

nodes:
- role: control-plane
  extraPortMappings:
    - containerPort: 30080
      hostPort: 30080
      protocol: TCP
```

The important point is that Kind nodes are Docker containers.

Therefore, a Kubernetes NodePort is not automatically equivalent to a port directly exposed on the host.

The `extraPortMappings` configuration maps:

```text
Host :30080
      ↓
Kind Node :30080
      ↓
Kubernetes NodePort
      ↓
Service
      ↓
Pod
```

---

# Kubernetes Service Networking

The API Service was initially:

```yaml
spec:
  type: ClusterIP
```

A ClusterIP is reachable only from within the Kubernetes cluster.

For local browser access, the API Service was changed to:

```yaml
spec:
  type: NodePort
```

The traffic flow becomes:

```text
Browser
   │
   ▼
localhost:30080
   │
   ▼
Kind Node
   │
   ▼
NodePort
   │
   ▼
Service port 5000
   │
   ▼
targetPort 5000
   │
   ▼
API Pod
```

A Kubernetes Service is an API abstraction; it does not literally "sit inside" a node.

Traffic forwarding is implemented on nodes through Kubernetes networking mechanisms such as kube-proxy/iptables/IPVS or an equivalent dataplane.

---

# Kubernetes Deployments

The application components are deployed using Kubernetes Deployments.

Example conceptual structure:

```text
Deployment
    │
    ▼
ReplicaSet
    │
    ├── Pod
    └── Pod
```

Deployments provide:

- Desired replica count
- Rolling updates
- ReplicaSet management
- Pod replacement
- Rollback capability

---

# Self-Healing

Kubernetes self-healing was verified by deleting application pods.

For example:

```bash
kubectl delete pod <pod-name>
```

The Deployment/ReplicaSet detects that the actual number of replicas is lower than the desired state.

Kubernetes automatically creates a replacement pod.

```text
Pod deleted
    ↓
ReplicaSet detects missing replica
    ↓
New Pod created
    ↓
Application returns to desired state
```

This demonstrates Kubernetes reconciliation and self-healing.

---

# Rolling Updates

The Jenkins deployment stage uses:

```bash
kubectl set image deployment/api-deployment \
    api-container=${DOCKER_USERNAME}/poc-api:${IMAGE_TAG}

kubectl set image deployment/worker-deployment \
    worker-container=${DOCKER_USERNAME}/poc-worker:${IMAGE_TAG}
```

Kubernetes then performs a rolling update.

Conceptually:

```text
Old Pods
   ↓
New image specified
   ↓
New Pods created
   ↓
New Pods become Ready
   ↓
Old Pods terminated
```

The pipeline also waits for rollout completion using:

```bash
kubectl rollout status
```

This prevents Jenkins from declaring deployment success before Kubernetes has completed the rollout.

---

# Image Versioning

Jenkins uses its build number as the Docker image tag.

Example:

```text
Jenkins Build #42
        ↓
poc-api:42
poc-worker:42
```

This is better than relying only on:

```text
latest
```

because every build produces an identifiable image.

However, changing the image using:

```bash
kubectl set image
```

does not itself create a version-controlled Kubernetes manifest.

A more production-oriented approach is:

```text
Git
 ├── Application source
 ├── Dockerfile
 └── Versioned Kubernetes manifests
```

and eventually a GitOps workflow using tools such as Argo CD or Flux.

---

# Jenkins Pipeline

The pipeline follows this general sequence:

```text
Checkout
   ↓
Build
   ↓
Test
   ↓
Docker Build
   ↓
Docker Login
   ↓
Docker Push
   ↓
Kubernetes Deploy
   ↓
Rollout Verification
```

The image tag is derived from:

```groovy
IMAGE_TAG = "${BUILD_NUMBER}"
```

Example:

```text
Build #42
    ↓
nitinxyz/poc-api:42
nitinxyz/poc-worker:42
```

---

# Docker Hub

After successful image builds, Jenkins authenticates with Docker Hub using Jenkins credentials.

Conceptually:

```bash
docker login
docker push nitinxyz/poc-api:${IMAGE_TAG}
docker push nitinxyz/poc-worker:${IMAGE_TAG}
```

Credentials are stored in Jenkins rather than hardcoded in the Jenkinsfile.

---

# GitHub Webhook

The repository is configured with a GitHub webhook.

Because Jenkins is running locally, GitHub cannot directly access:

```text
localhost:9090
```

ngrok provides a public HTTPS tunnel:

```text
GitHub
   │
   ▼
ngrok public URL
   │
   ▼
localhost:9090
   │
   ▼
Jenkins
```

The webhook endpoint is:

```text
/github-webhook/
```

The Jenkins job uses the trigger:

```text
GitHub hook trigger for GITScm polling
```

with the pipeline configured as:

```text
Pipeline script from SCM
```

Therefore:

```text
git push
   ↓
GitHub webhook
   ↓
Jenkins
   ↓
SCM checkout
   ↓
Jenkinsfile
   ↓
Pipeline execution
```

---

# Local Development vs CI/CD

Docker Compose is used for local infrastructure/development workflows.

The CI/CD Compose setup primarily runs Jenkins.

The application deployment target is Kubernetes.

Therefore:

```text
Docker Compose
    → Local development / Jenkins infrastructure

Kubernetes
    → Application deployment target
```

The two environments serve different purposes and are not competing deployment mechanisms.

---

# Repository Structure

The project is organized around application code, Docker configuration, Kubernetes manifests, and Jenkins configuration.

A representative structure is:

```text
poc/
├── api/
│   ├── Dockerfile
│   └── application source
│
├── worker/
│   ├── Dockerfile
│   └── worker source
│
├── k8s/
│   ├── api-deployment.yaml
│   ├── api-service.yaml
│   ├── worker-deployment.yaml
│   ├── redis-deployment.yaml
│   └── ...
│
├── jenkins/
│   ├── Dockerfile
│   └── config.jenkins
│
├── Jenkinsfile
├── docker-compose.yml
├── .dev.yaml
└── kind-config.yaml
```

> Adjust filenames above if the repository contains additional or differently named manifests.

---

# Complete Deployment Lifecycle

## 1. Developer changes code

```bash
git add .
git commit -m "Update API"
git push
```

## 2. GitHub receives the push

GitHub sends a webhook to Jenkins through ngrok.

## 3. Jenkins starts

Jenkins checks out the repository and loads the `Jenkinsfile`.

## 4. Docker images are built

```text
poc-api:<BUILD_NUMBER>
poc-worker:<BUILD_NUMBER>
```

## 5. Images are pushed

```text
Docker Hub
   ↑
   │
Jenkins
```

## 6. Kubernetes deployment is updated

```bash
kubectl set image ...
```

## 7. Kubernetes performs rolling update

Old pods are gradually replaced with new pods.

## 8. Rollout is verified

```bash
kubectl rollout status ...
```

## 9. Application is accessed

The NodePort exposes the application to the host.

## 10. Self-healing

If a managed pod is deleted, Kubernetes recreates it automatically.

---

# Troubleshooting & Errors

The following issues were encountered and resolved while building the project.

---

## 1. Docker daemon socket permission denied

### Error

```text
permission denied while trying to connect to the Docker daemon socket
```

### Cause

The Docker CLI inside Jenkins was trying to access:

```text
/var/run/docker.sock
```

but the `jenkins` user did not have permission to access the socket.

### Debugging

Checked the socket:

```bash
ls -l /var/run/docker.sock
```

The socket belonged to the `docker` group.

Checked the host Docker group:

```bash
getent group docker
```

### Fix

Matched the Docker group GID inside the Jenkins image and added Jenkins to the group:

```dockerfile
RUN groupmod -g 989 docker && \
    usermod -aG docker jenkins
```

After rebuilding the Jenkins image, Jenkins could use Docker successfully.

---

## 2. Docker image `ubuntu:24.04-minimal` not found

### Error

```text
ubuntu:24.04-minimal: not found
```

### Cause

The requested image/tag did not exist in Docker Hub under that name.

### Debugging

Docker failed while resolving:

```text
docker.io/library/ubuntu:24.04-minimal
```

### Fix

Changed the base image to an available Ubuntu tag.

---

## 3. Docker Hub DNS resolution failure

### Error

```text
dial tcp: lookup registry-1.docker.io: no such host
```

### Cause

The Docker daemon could not resolve the Docker Hub registry hostname.

### Debugging

The failure occurred during:

```bash
docker login
```

and specifically while the Docker daemon attempted to contact:

```text
registry-1.docker.io
```

### Resolution

Investigated Docker/host networking and DNS configuration. The issue was eventually resolved and the pipeline successfully authenticated with Docker Hub.

---

## 4. Jenkins kubeconfig mount: "not a directory"

### Error

```text
not a directory
```

during the Docker Compose mount of:

```text
~/.kube/config.jenkins
```

### Cause

`config.jenkins` had accidentally become a directory instead of a file.

### Debugging

Removed the incorrect path:

```bash
rm -rf ~/.kube/config.jenkins
```

Then recreated it:

```bash
cp ~/.kube/config ~/.kube/config.jenkins
```

---

## 5. Stale `.kube/config` directory in Jenkins volume

### Problem

Even after fixing the host kubeconfig, Docker continued to behave as though:

```text
/var/jenkins_home/.kube/config
```

was a directory.

### Cause

The named Docker volume:

```text
poc_jenkins_home
```

contained an old `.kube/config` directory.

### Debugging

Inspected the volume:

```bash
docker run --rm \
  -v poc_jenkins_home:/data \
  alpine ls -lR /data/.kube
```

### Fix

Removed only the stale directory:

```bash
docker run --rm \
  -v poc_jenkins_home:/data \
  alpine rm -rf /data/.kube/config
```

---

## 6. Kubeconfig `localhost` problem

### Problem

The host kubeconfig contained:

```text
server: https://127.0.0.1:<random-port>
```

This worked from the host but failed from Jenkins.

### Cause

Inside the Jenkins container:

```text
127.0.0.1
```

refers to Jenkins itself.

It does not refer to the host or the Kind control-plane container.

### Fix

Connected Jenkins to the external Docker `kind` network and changed the Kubernetes API endpoint to:

```text
https://self-healing-cluster-control-plane:6443
```

This allowed Jenkins to resolve and reach the Kind control plane directly.

---

## 7. Jenkins kubeconfig disappeared because of the Jenkins volume

### Problem

The kubeconfig was copied into:

```text
/var/jenkins_home/.kube/config
```

inside the Jenkins image but was not available as expected at runtime.

### Cause

The named volume:

```text
jenkins_home
```

mounted over:

```text
/var/jenkins_home
```

and therefore masked files baked into that directory during image build.

### Fix

Moved the kubeconfig outside the Jenkins home volume:

```text
/usr/local/share/kube/config
```

and configured:

```groovy
environment {
    KUBECONFIG = "/usr/local/share/kube/config"
}
```

This avoided the volume masking problem.

---

## 8. Kubernetes TLS certificate error

### Error

```text
tls: failed to verify certificate:
x509: certificate signed by unknown authority
```

### Cause

The kubeconfig's cluster certificate/CA information was inconsistent with the recreated Kind cluster.

Kind generates cluster-specific certificates.

### Debugging

Compared the kubeconfig and the current Kind cluster after cluster recreation.

### Resolution

Regenerated/updated the Jenkins kubeconfig from the current Kind cluster configuration and ensured Jenkins used the matching API endpoint and CA data.

Final validation:

```bash
kubectl get nodes
```

returned:

```text
self-healing-cluster-control-plane   Ready
```

---

## 9. `/version` endpoint did not appear

### Problem

The `/version` route was added to Flask, but:

```bash
flask routes
```

or the deployed application did not show the expected endpoint.

### Cause

The Kubernetes pod was still running an older Docker image.

Changing source code does not change an already-built image.

### Important concept

```text
Source code change
      ≠
Running container change
```

A new image must be built and deployed.

### Fix

Rebuilt the application image and redeployed it.

---

## 10. Worker container name not found

### Error

```text
unable to find container named worker-container
```

### Cause

`kubectl set image` references the Kubernetes container name, not the Deployment name.

The command used:

```bash
kubectl set image deployment/worker-deployment \
    worker-container=...
```

The container name therefore had to exactly match:

```yaml
containers:
- name: worker-container
```

### Debugging

Checked the Deployment manifest and corrected the mismatch.

---

## 11. Browser/API `ERR_CONNECTION_REFUSED`

### Error

```text
Failed to load resource:
net::ERR_CONNECTION_REFUSED
```

and:

```text
TypeError: Failed to fetch
```

### Cause

The frontend/backend configuration was still attempting to communicate with an inaccessible localhost endpoint.

### Debugging

The browser developer console showed the failed request.

The application was then started correctly on the server, and the endpoint configuration was corrected.

### Result

The application became reachable successfully.

---

## 12. GitHub webhook HTTP 403

### Error

GitHub webhook delivery initially returned:

```text
HTTP 403
No valid crumb was included in the request
```

### Cause

Jenkins CSRF protection rejected the webhook request because the Jenkins webhook integration was not configured correctly.

### Debugging

Checked the webhook delivery response in GitHub.

### Fix

Installed/configured the Jenkins GitHub Integration functionality and used the Jenkins GitHub webhook endpoint:

```text
/github-webhook/
```

After configuration, webhook redelivery returned:

```text
HTTP 200
```

The Jenkins pipeline then triggered successfully.

---

## 13. Kind API server port confusion

### Problem

The Kind kubeconfig contained an endpoint such as:

```text
127.0.0.1:<random-port>
```

while the Kubernetes API server internally listens on:

```text
6443
```

### Cause

Kind maps the container's port `6443` to a dynamically assigned host port.

Therefore:

```text
Host:
127.0.0.1:<random-port>

Kind network:
self-healing-cluster-control-plane:6443
```

Both are valid, but for different network locations.

### Final approach

Host:

```text
127.0.0.1:<mapped-port>
```

Jenkins:

```text
self-healing-cluster-control-plane:6443
```

---

# Important Concepts Learned

## Docker CLI vs Docker Daemon

```text
docker command
     ↓
Docker CLI
     ↓
Docker socket
     ↓
Docker daemon
```

The CLI sends requests; the daemon performs the actual Docker operations.

---

## Kubernetes Desired vs Actual State

Kubernetes continuously reconciles:

```text
Desired State
      ↕
Actual State
```

Example:

```text
Desired replicas = 2
Actual replicas  = 1

        ↓

Kubernetes creates another pod
```

This reconciliation loop is the basis of Kubernetes self-healing.

---

## Deployment vs ReplicaSet vs Pod

```text
Deployment
    │
    ▼
ReplicaSet
    │
    ├── Pod
    └── Pod
```

The Deployment manages the desired application version and rollout.

The ReplicaSet maintains the desired number of pods.

Pods run the actual containers.

---

## Service vs Pod

Pods are ephemeral.

Their IP addresses can change.

A Service provides a stable networking abstraction:

```text
Client
  ↓
Service
  ↓
Pod
```

The Service selects pods using labels.

---

## NodePort

NodePort exposes a Service through a port on Kubernetes nodes:

```text
Node IP:NodePort
      ↓
Service
      ↓
Pod
```

With Kind, an additional host-to-node port mapping is required for browser access from the host.

---

# Current Successful State

The final project successfully demonstrated:

```text
GitHub Push
     ↓
GitHub Webhook
     ↓
ngrok
     ↓
Jenkins
     ↓
Docker Build
     ↓
Docker Hub Push
     ↓
kubectl set image
     ↓
Kind Kubernetes
     ↓
Rolling Update
     ↓
Updated Application
```

And independently:

```text
Pod Failure
     ↓
ReplicaSet detects failure
     ↓
Replacement Pod
     ↓
Application restored
```

Therefore both the **CI/CD pipeline** and **Kubernetes self-healing behavior** were successfully verified.

---

# Production Improvements / Next Stage

The current project intentionally uses:

```text
Jenkins
    ↓
kubectl set image
    ↓
Kubernetes
```

This is suitable for learning CI/CD mechanics but can be improved.

### Planned Stage 2

- Kubernetes readiness probes
- Kubernetes liveness probes
- Deployment rollback
- Explicit manifest versioning
- Better image tagging
- Deployment history
- Automated health verification
- Failure/rollback testing

### GitOps Stage

Eventually move deployment responsibility from Jenkins to a GitOps controller:

```text
Developer
   ↓
GitHub
   ↓
CI Pipeline
   ↓
Build + Push Image
   ↓
Update Kubernetes Manifest
   ↓
Git Repository
   ↓
Argo CD / Flux
   ↓
Kubernetes
```

This separates:

```text
CI → Build/Test/Publish

CD → Reconcile Git state with Kubernetes
```

---

# Key Commands

### Check Kubernetes nodes

```bash
kubectl get nodes
```

### Check all pods

```bash
kubectl get pods
```

### Check Deployments

```bash
kubectl get deployments
```

### Check Services

```bash
kubectl get svc
```

### Check pod details

```bash
kubectl describe pod <pod-name>
```

### Check logs

```bash
kubectl logs <pod-name>
```

### Delete a pod to test self-healing

```bash
kubectl delete pod <pod-name>
```

### Check Deployment rollout

```bash
kubectl rollout status deployment/<deployment-name>
```

### View Deployment history

```bash
kubectl rollout history deployment/<deployment-name>
```

### Roll back a Deployment

```bash
kubectl rollout undo deployment/<deployment-name>
```

### Check Docker socket

```bash
ls -l /var/run/docker.sock
```

### Check Docker networks

```bash
docker network ls
```

### Inspect Kind network

```bash
docker network inspect kind
```

---

# Lessons from the Project

1. **A containerized Jenkins does not automatically have access to Docker.**  
   The Docker socket and permissions must be configured.

2. **A container's `localhost` is not the host's `localhost`.**

3. **Docker networks determine container-to-container reachability.**

4. **Kind Kubernetes nodes are Docker containers**, so host access may require explicit port mappings.

5. **Changing source code does not update a running container.**  
   A new image must be built and deployed.

6. **`kubectl set image` changes the Deployment's pod template**, triggering a Kubernetes rollout.

7. **A Kubernetes Service is an abstraction**, not a process running inside a node.

8. **Deployments provide self-healing indirectly through ReplicaSets.**

9. **`latest` is convenient but poor for reproducibility.**  
   Immutable/versioned image tags are preferable.

10. **CI/CD and GitOps solve different parts of deployment automation.**  
    Jenkins can build and publish artifacts, while GitOps tools can continuously reconcile Kubernetes state.

---

# Project Outcome

The project successfully demonstrates an end-to-end DevOps workflow:

**Source Control → Automated CI/CD → Container Build → Registry → Kubernetes Deployment → Rolling Update → Self-Healing**

It provides a practical foundation for moving toward a more production-oriented architecture using:

**Versioned manifests → Rollbacks → Health probes → GitOps → Argo CD/Flux**