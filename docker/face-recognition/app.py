import json
import urllib.parse
import boto3
import torch
import os
import subprocess

# import cv2

print('Loading function')

# print(cv2.__version__)

AWS_REGION = 'us-east-1'
OUPUT_TOPIC_ARN = 'arn:aws:sns:us-east-1:942600870808:g45-academic-records.fifo'
MESSAGE_GROUP_ID = 'face-recognition-results'


def parse_results(results):
    if not results:
        print("empty results are sent")
        return None, None
    predictionList = results[results.find('(') + 1:results.find(')')].split(",")
    label = predictionList[1].strip()
    key = predictionList[0].strip()
    return key, label


def publish_message_to_pi(message):
    sns = boto3.client("sns", region_name=AWS_REGION)
    response = sns.publish(
        TopicArn=OUPUT_TOPIC_ARN,
        # TargetArn='',
        Message=message,
        MessageGroupId=MESSAGE_GROUP_ID
    )
    return response


def lambda_handler(event, context):
    s3 = boto3.client('s3', region_name=AWS_REGION)
    # print("Received event: " + json.dumps(event, indent=2))

    # Get the object from the event and show its content type
    bucket = event['Records'][0]['s3']['bucket']['name']
    # print(bucket)
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
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
            result = subprocess.run(['/bin/sh', 'run_prediction.sh', frame_path], capture_output=True, check=True). \
                stdout.decode().strip()
            # print("ashish results: " + str(result))
            print("subprocess run successfully")
        except subprocess.CalledProcessError as e:
            print("Subprocess failed : " + str(e.output))
        _, label = parse_results(result)
        # print(dictResult)
        # print(label)
        # Fetching the database based on results.
        dynamodb = boto3.client('dynamodb', region_name=AWS_REGION)
        table_name = "g45-records-table"
        table_key = {
            'Name': {'S': str(label)}
        }
        response = dynamodb.get_item(TableName=table_name, Key=table_key)
        # print(response)
        id_student = response['Item']['Id']['S']
        Year = response['Item']['Year']['S']
        Major = response['Item']['Major']['S']
        result = "Id: " + str(id_student) + " Name: " + str(label) + " Major: " + str(Major) + " Year: " + str(Year)
        message = json.dumps({"key" : key, "message": str(result)})
        print("Message : " + str(message))
        publish_message_to_pi(str(message))
        try:
            os.remove(frame_path)
        except OSError as e:
            print("File Remove error: {} - {}".format(e.filename, e.strerror))
        # print("CONTENT TYPE: " + response['ContentType'] + " ashish")
        return label
    except Exception as e:
        print(e)
        print(
            'Error getting object {} from bucket {}. Make sure they exist and your bucket is in the same region as '
            'this function.'.format(
                key, bucket))
        raise e


if __name__ == "__main__":
    path = os.path.join(os.getcwd(), 'events', 'event.json')
    print(path)
    f = open(path)
    event = json.load(f)
    lambda_handler(event, None)
