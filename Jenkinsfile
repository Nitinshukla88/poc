pipeline {
	agent any
	environment {
		DOCKER_USERNAME = "nitinxyz"		
	} 
	stages {
		stage('SCM Skip') {
            		steps {
                		scmSkip(
                    			deleteBuild: true,
                    			skipPattern: '.*\\[jenkins-deploy\\].*'
                		)
            		}
        	}
		stage('Get Git Commit') {
            		steps {
                		script {
                    			env.IMAGE_TAG = sh(
                        			script: "git rev-parse --short HEAD",
                        			returnStdout: true
                    			).trim()

                    			echo "Git commit: ${env.IMAGE_TAG}"
                		}
            		}
        	}
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
        			}
    			}
		}
		stage('Update Manifest') {
    			steps {
        			sh '''
            				sed -i "s|image: nitinxyz/poc-api:.*|image: nitinxyz/poc-api:${IMAGE_TAG}|" k8s/api-deployment.yaml

            				echo "Updated API manifest:"
            				grep "image:" k8s/api-deployment.yaml
        			'''
    			}
		}
		stage('Commit and Push Manifest') {
    			steps {
        			sshagent(['github-jenkins-ssh']) {
            				sh '''
                				git add k8s/api-deployment.yaml

                				git commit -m "Update API image to ${IMAGE_TAG} [jenkins-deploy]"

                				git push origin HEAD:main
            				'''
        			}
    			}
		}
	}
}
