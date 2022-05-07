# CloudComputing
The face recognition project using Raspberry pi and AWS backend compeleted as part of CSE546 coursework.

## Group 45:
. Ashish Kumar Rambhatla (1215350552)
. Chaitanya Prakash Poluri (1223158937)
. Reethu C Vattikunta	(1222619619)

-> Steps to run the code:

1.	Create docker image:
	docker build -t <image_name>:<version_number> .
	docker images – This will list all the created docker images.
	docker tag <local_image_tag> <AWS_ACCOUNT_ID>.dkr.ecr.<AWS_REGION>.aws.amazon.com
	docker login -u AWS -p $(aws ecr get-login-password --region <aws_region>) <aws_ecr_repo_uri>
	docker tag <local_docker_image_id> <aws_ecr_repo_uri>:<image_version>
	docker push <AWS_ECR_REPO_URI>:<image_version>
2. 	Create a table(students) in DynamoDB from AWS console with the attributes id, name, major, year and name as the partition key. Later add, few rows to the database.
3.	Create AWS Lambda function with the container image URI from AWS console.
4.	Copy demo.py file and requirements.txt file on to the Raspberry Pi desktop.
5.	Install the requirements using ‘pip3 install -r requirements.txt’
6.	Run the demo.py using ‘python3 demo.py’

