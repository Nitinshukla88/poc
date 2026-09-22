pipeline {
	agent any
	environment {
		DOCKER_USERNAME = "nitinxyz"
		IMAGE_TAG = "${BUILD_NUMBER}"		
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
		stage('Get Previous Version') {
    			steps {
        			script {
            				env.PREVIOUS_IMAGE = sh(
                			script: "grep 'image: nitinxyz/poc-api:' k8s/api-deployment.yaml | awk '{print \$2}'",
                			returnStdout: true
            				).trim()

            				echo "Previous image: ${env.PREVIOUS_IMAGE}"
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
		stage('Deploy') {
			steps {
				script {
					try {
						sh '''
							kubectl apply -f k8s/api-deployment.yaml
							kubectl rollout status deployment/api-deployment --timeout=60s
						'''
					} catch (Exception e) {

						echo "Deployment failed. Rolling back..."
						sh '''
							kubectl rollout undo deployment/api-deployment
							kubectl rollout status deployment/api-deployment --timeout=60s

							echo "Restoring Git manifest to ${PREVIOUS_IMAGE}"

        						sed -i "s|image: nitinxyz/poc-api:.*|image: ${PREVIOUS_IMAGE}|" k8s/api-deployment.yaml

        						echo "Manifest after rollback:"
        						grep "image:" k8s/api-deployment.yaml
						'''

						sshagent(['github-jenkins-ssh']) {
    							sh '''
        							git add k8s/api-deployment.yaml

        							git commit -m "Rollback API image to ${PREVIOUS_IMAGE} [jenkins-deploy]"

        							git push origin HEAD:main
    							'''
						}
						throw e
					}
				}
			}
		}
	}
}
