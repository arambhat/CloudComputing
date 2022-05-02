import time

import boto3
from botocore.exceptions import NoCredentialsError
import subprocess
from picamera.array import PiRGBArray
from picamera import PiCamera
import cv2
import threading
from datetime import datetime
import os
import errno

VIDEO_DURATION_IN_MILLIS = 4000
VIDEO_FORMAT = '.mp4'
IMAGE_FORMAT = '.png'
NUM_FRAMES = 600  # 5 minutes video == 600 frames @ 2 frames/sec.
AWS_REGION = "us-east-1"
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


def uploadFrame(image, image_name):
    s3 = boto3.client("s3", region_name=AWS_REGION)
    image_path = os.path.join(os.getcwd(), image_name)
    result = False
    try:
        s3.upload_file(image_path, s3InputBucket, image_name)
        result = True
        print("Frame Upload Successful!")
    except FileNotFoundError:
        print("The file was not found!")
    except NoCredentialsError:
        print("Credentials not found!!")
    return result


def recordVideo():
    camera = PiCamera()
    camera.resolution = (640, 640);
    camera.framerate = 2
    capture_object = PiRGBArray(camera, size=(640, 640))
    time.sleep(0.1)  # For the camera to get setup.
    frame_count = 0
    bucket_params = {'name': s3InputBucket, 'region': AWS_REGION}
    # A one time check to make sure the input bucket exists in the AWS.
    # If it doesn't exist, the below API call will create one.
    getS3Bucket(bucket_params)

    for frame in camera.capture_continuous(capture_object, format='rgb', use_video_port=True):
        frame_count = frame_count + 1
        image = frame.array
        timestamp = datetime.now()
        timestamp = timestamp.strftime("%d_%m_%Y_%H_%M_%S")
        image_name = timestamp + IMAGE_FORMAT
        cv2.imwrite(image_name, image)
        response = uploadFrame(image, image_name)
        if response:
            try:
                os.remove(os.path.join(os.getcwd(), image_name))
                print("Local file deleted!")
            except OSError as e:
                if e.errno != errno.ENOENT:
                    print("File does not exist, so ignoring deletion")
                else:
                    print("Error in deleting " + image_name + " file")
        if frame_count == NUM_FRAMES:
            break


if __name__ == '__main__':
    recordVideo()
