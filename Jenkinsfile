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
					
					if (!env.PREVIOUS_IMAGE) {
                				error "Could not determine PREVIOUS_IMAGE from k8s/api-deployment.yaml"
            				}

            				if (!(env.PREVIOUS_IMAGE ==~ /nitinxyz\/poc-api:\S+/)) {
                				error "Invalid PREVIOUS_IMAGE: ${env.PREVIOUS_IMAGE}"
            				}
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

							kubectl run health-check \
            						--rm \
							-i \
           						--restart=Never \
            						--image=curlimages/curl \
            						-- curl --fail http://api-service:5000/version

        						echo "Application health check successful."
						'''
					} catch (Exception e) {

						echo "Deployment failed. Rolling back..."
						try {
        						sh '''
            							kubectl rollout undo deployment/api-deployment
            							kubectl rollout status deployment/api-deployment --timeout=60s
        						'''

        						echo "Kubernetes rollback succeeded."

    						} catch (Exception rollbackError) {

        						echo "Kubernetes rollback FAILED."

        						error "CRITICAL: Deployment failed and Kubernetes rollback also failed."
    						}

						sh '''

							echo "Restoring Git manifest to ${PREVIOUS_IMAGE}"

        						sed -i "s|image: nitinxyz/poc-api:.*|image: ${PREVIOUS_IMAGE}|" k8s/api-deployment.yaml

        						echo "Manifest after rollback:"
        						grep "image:" k8s/api-deployment.yaml
						'''

						try {
    							sshagent(['github-jenkins-ssh']) {

        							sh '''
            								git add k8s/api-deployment.yaml

									if git diff --cached --quiet; then
                								echo "No Git manifest changes to commit."
            								else
                								git commit -m "Rollback API image to ${PREVIOUS_IMAGE} [jenkins-deploy]"
                								git push origin HEAD:main
            								fi
        							'''
    							}

    							echo "Git manifest rollback succeeded."

						} catch (Exception gitError) {

    							echo "Git manifest rollback FAILED."

    							error "CRITICAL: Kubernetes rolled back successfully, but Git manifest rollback failed."
						}
						throw e
					}
				}
			}
		}
	}
}
