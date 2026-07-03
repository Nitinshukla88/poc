FROM jenkins/jenkins:lts

USER root 

RUN apt-get update && \
    apt-get install -y docker.io && \
    apt-get clean

RUN groupmod -g 989 docker && \
    usermod -aG docker jenkins

USER jenkins
