pipeline {
	agent any
	environment {
		DOCKER_USERNAME = "nitinxyz"
		IMAGE_TAG = "latest"		
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
	}
}
