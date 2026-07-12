FROM jenkins/jenkins:lts

USER root 

RUN apt-get update && \
    apt-get install -y docker.io curl && \
    apt-get clean

RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"

RUN chmod +x kubectl && \
    mv kubectl /usr/local/bin/

RUN mkdir -p /usr/local/share/kube

COPY config.jenkins /usr/local/share/kube/config

RUN groupmod -g 1001 docker && \
    usermod -aG docker jenkins

USER jenkins
