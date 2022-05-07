import json
import boto3
import time
import os
from custom_encoder import CustomEncoder
import subprocess

# import cv2

print('Loading function')

# print(cv2.__version__)

AWS_REGION = 'us-east-1'
OUPUT_TOPIC_ARN = 'arn:aws:sns:us-east-1:942600870808:g45-academic-records.fifo'
MESSAGE_GROUP_ID = 'face-recognition-results'

getMethod = 'GET'
postMethod = 'POST'

healthPath = '/health'
recognitionPath = '/facerecogition'


def parse_results(results):
    if not results:
        print("empty results are sent")
        return None, None
    predictionList = results[results.find('(') + 1:results.find(')')].split(",")
    label = predictionList[1].strip()
    key = predictionList[0].strip()
    return key, label


def buildResponse(statusCode, body=None):
    response = {
        'statusCode': statusCode,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        }
    }
    if body is not None:
        response['body'] = json.dumps(body, cls=CustomEncoder)
    return response


def runFaceRecognition(bucket, image_name):
    s3 = boto3.client('s3', region_name=AWS_REGION)
    key = image_name
    try:
        frame_download_path = "/tmp"
        frame_path = os.path.join(frame_download_path, '{}'.format(key))
        with open(frame_path, 'wb') as data:
            s3.download_fileobj(bucket, key, data)
            if os.path.exists(frame_path):
                print("File written to /tmp successfully. path is : " + str(frame_path))
            else:
                print("File not found error!")
        result = []
        print("-----results-------")
        try:
            start = time.time()
            result = subprocess.run(['/bin/sh', 'run_prediction.sh', frame_path], capture_output=True, check=True). \
                stdout.decode().strip()
            end = time.time()
            eval_run_time = end - start
            print(f"subprocess run successfully with run time of: {eval_run_time:.2f}s")
        except subprocess.CalledProcessError as e:
            print("Subprocess failed : " + str(e.output))
        _, label = parse_results(result)
        # Fetching the database based on results.
        dynamodb = boto3.client('dynamodb', region_name=AWS_REGION)
        table_name = "g45-records-table"
        table_key = {
            'Name': {'S': str(label)}
        }
        db_response = dynamodb.get_item(TableName=table_name, Key=table_key)
        # print(response)
        id_student = db_response['Item']['Id']['S']
        Year = db_response['Item']['Year']['S']
        Major = db_response['Item']['Major']['S']
        result = "Id: " + str(id_student) + " Name: " + str(label) + " Major: " + str(Major) + " Year: " + str(Year)
        body = {"key": key, "response": str(result)}
        pi_response = buildResponse(200, body)
        print("Message : " + str(pi_response))
        try:
            os.remove(frame_path)
        except OSError as e:
            print("File Remove error: {} - {}".format(e.filename, e.strerror))
        # print("CONTENT TYPE: " + response['ContentType'] + " ashish")
        return pi_response
    except Exception as e:
        print(e)
        print(
            'Error getting object {} from bucket {}. Make sure they exist and your bucket is in the same region as '
            'this function.'.format(
                key, bucket))
        raise e


def lambda_handler(event, context):
    print(json.dumps(event, indent=2))
    httpMethod = event['httpMethod']
    path = event['path']
    if httpMethod == getMethod and path == healthPath:
        response = buildResponse(200)
    elif httpMethod == getMethod and path == recognitionPath:
        bucket_name = event['queryStringParameters']['BucketName']
        image_name = event['queryStringParameters']['ImageName']
        response = runFaceRecognition(bucket_name, image_name)
    else:
        response = buildResponse(404, 'Request Not Found!!')
    return response


if __name__ == "__main__":
    path = os.path.join(os.getcwd(), 'events', 'event.json')
    print(path)
    f = open(path)
    event = json.load(f)
    lambda_handler(event, None)
