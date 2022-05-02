import boto3
from botocore.exceptions import NoCredentialsError
import subprocess
import threading
from datetime import datetime
import os
import errno

VIDEO_DURATION_IN_MILLIS = 4000
VIDEO_FORMAT = '.mp4'

awsRegion = "us-east-1"
s3InputBucket = "g45-vid-input-bucket"
s3outputBucket = "g45-output-bucket"


def createS3Bucket(bucketParams) -> object:
    """

    : param bucketParams {"name": <string>, "region": <AWS_REGION_NAME>}
    : return bucket
    """
    s3 = boto3.resource("s3", region_name=bucketParams["region"])
    bucket = s3.create_bucket(Bucket=bucketParams["name"])
    print("create bucket is successfully done")
    return bucket


def getS3Bucket(bucketParams) -> object:
    """
    : param bucketParams {"name": <string>, "region": <AWS_REGION_NAME>}
    : return bucket
    """
    s3 = boto3.resource("s3", region_name=bucketParams["region"])
    buckets = s3.buckets.all()
    # check if the required s3 bucket is already present
    for bucket in buckets:
        if bucket.name == bucketParams["name"]:
            print("found the required bucket -- {bucket.name}")
            return bucket
    bucket = createS3Bucket(bucketParams)
    return bucket


def recordVideos(videoParams):
    name = videoParams["name"]
    duration = videoParams["duration"]
    result = subprocess.run(['raspivid', '-o', name, '-t', duration],
                            capture_output=True).stdout.decode().strip()
    print(result)


def uploadVideo(uploadParams):
    videoName = uploadParams['name']
    print("videoName: " + videoName)
    filePath = uploadParams['path']
    videoPath = os.path.join(filePath, videoName)
    print("final file path " + videoPath)
    s3 = boto3.client("s3", region_name=awsRegion)
    try:
        s3.upload_file(videoPath, s3InputBucket, videoName)
        print("Upload Successful!")
    except FileNotFoundError:
        print("The file was not found!")
    except NoCredentialsError:
        print("Credentials not found!!")
    try:
        #os.remove(videoPath)
        print("Local file deleted!")
    except OSError as e:
        if e.errno != errno.ENOENT:
            print("File does not exist, so ignoring deletion")
        else:
            print("Error in deleting " + videoName + " file")


if __name__ == '__main__':
    count = 1
    while count > 0:
        timestamp = datetime.now()
        timestamp = timestamp.strftime("%d_%m_%Y_%H_%M_%S")
        videoName = timestamp + VIDEO_FORMAT
        print(videoName)
        print(type(videoName))
        ''' 10 seconds in milliseconds.'''
        duration = VIDEO_DURATION_IN_MILLIS
        print(type(str(duration)))
        videoParams = {'name': videoName, 'duration': str(duration)}
        recordVideos(videoParams)
        filepath = os.getcwd()
        print(filepath)
        uploadParams = {'name': videoName, 'path': filepath}
        uploadVideo(uploadParams)
        count = count - 1
