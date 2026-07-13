pipeline {
	agent any
	environment {
		DOCKER_USERNAME = "nitinxyz"
		IMAGE_TAG = "${BUILD_NUMBER}"		
	} 
	stages {
		stage('Test') {
			agent {
				docker {
					image 'python:3.11-slim'
				}
			}
			steps {
				sh '''
					python -m venv venv 
					. venv/bin/activate
					pip install --upgrade pip
					pip install -r api/requirements.txt
					pytest api/test_app.py
				'''
			}
		}
		stage('Build') {
			steps {
				sh "docker build -t ${DOCKER_USERNAME}/poc-api:${IMAGE_TAG} ./api"
				sh "docker build -t ${DOCKER_USERNAME}/poc-worker:${IMAGE_TAG} ./worker"
			}
		}
		stage('Push') {
    			steps {
        			withCredentials([usernamePassword(
            				credentialsId: 'poc-jenkins',
            				usernameVariable: 'USERNAME',
            				passwordVariable: 'PASSWORD'
        			)]) {
            				sh "echo $PASSWORD | docker login -u $USERNAME --password-stdin"
            				sh "docker push ${DOCKER_USERNAME}/poc-api:${IMAGE_TAG}"
            				sh "docker push ${DOCKER_USERNAME}/poc-worker:${IMAGE_TAG}"
        			}
    			}
		}
		stage('Deploy') {
			steps {
				sh '''
					kubectl set image deployment/api-deployment \
						api-container=${DOCKER_USERNAME}/poc-api:${IMAGE_TAG}
					
					kubectl rollout status deployment/api-deployment

					kubectl set image deployment/worker-deployment \
						worker-container=${DOCKER_USERNAME}/poc-worker:${IMAGE_TAG}

					kubectl rollout status deployment/worker-deployment
				'''
			}
		}	
	}
}
