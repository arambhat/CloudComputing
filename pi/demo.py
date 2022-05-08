import time
from threading import Timer
import requests
import boto3
from botocore.exceptions import NoCredentialsError
import subprocess
from picamera.array import PiRGBArray
from picamera import PiCamera
from concurrent.futures import ThreadPoolExecutor
import cv2
import threading
from datetime import datetime
import os
import errno

VIDEO_DURATION_IN_MILLIS = 4000
IMAGE_FORMAT = '.png'
FRAME_RATE = 20
NUM_FRAMES = 600  # 5 minutes video == 600 frames @ 2 frames/sec.
MAX_WORKERS = 1
AWS_REGION = "<YOUR_AWS_REGION>"
s3InputBucket = "<S3_BUCKET_NAME_FOR_FRAMES>"
s3VideoBucket = "<S3_BUCKET_NAME_FOR_VIDEOS>"
finalVideoName = "finalDemoVideo.mp4"
faceRecognitionApiUrl = "<FACERECOGNITION_API_END_POINT_URL>"


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
            print("found the required bucket -- {bucket}".format(bucket=bucket.name))
            return bucket
    bucket = createS3Bucket(bucketParams)
    return bucket


def uploadFrame(image_name):
    print("Uploading: " + str(image_name))
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
    
    try:
        os.remove(image_path)
        print("Local file deleted!")
    except OSError as e:
        if e.errno != errno.ENOENT:
            print("File does not exist, so ignoring deletion")
        else:
            print("Error in deleting " + image_name + " file")
    return result


def sendGetRecognitionRequest(request):
    headers = {"Content-Type": "application/json"}
    start_timestamp = datetime.now()
    http_response = requests.get(url=faceRecognitionApiUrl, params=request, headers=headers)
    end_time = datetime.now()
    latency = end_time - start_timestamp
    print(http_response.text)
    print("latency: " + str(round(latency.total_seconds(), 2)) + " seconds")


def uploadFrameAndRequestRecognition(image_name):
    response = uploadFrame(image_name)
    if response:
        request = {
            "ImageName": image_name,
            "BucketName": "g45-frame-extraction-bucket"
        }
        sendGetRecognitionRequest(request)
    return response

def recordVideo():
    camera = PiCamera()
    camera.resolution = (640, 640);
    camera.framerate = 30
    capture_object = PiRGBArray(camera, size=(640, 640))
    time.sleep(0.1)  # For the camera to get setup.
    # Initialising the opencv video writer object.
    video_path = os.path.join(os.getcwd(), finalVideoName)
    w, h = (640, 640)
    fourcc = cv2.VideoWriter_fourcc('m', 'p', '4', 'v')
    fps = FRAME_RATE
    writer = cv2.VideoWriter(video_path, fourcc, fps, (w, h))
    frame_count = 0
    bucket_params = {'name': s3InputBucket, 'region': AWS_REGION}
    # A one time check to make sure the input bucket exists in the AWS.
    # If it doesn't exist, the below API call will create one.
    getS3Bucket(bucket_params)
    timestamp = 0
    for frame in camera.capture_continuous(capture_object, format='bgr', use_video_port=True):
        frame_count = frame_count + 1
        image = frame.array
        # The image is saved into the output video file.
        writer.write(image)
        timestamp = timestamp + 1
        image_name = str(timestamp) + IMAGE_FORMAT
        resize_dimensions = (160, 160)
        resize_image = cv2.resize(image, resize_dimensions, interpolation=cv2.INTER_AREA)
        capture_object.truncate(0)
        # Upload one frame in every (FRAME_REATE/2) frames. (0.5 seconds)
        if frame_count % (FRAME_RATE/2) == 0:
            cv2.imwrite(image_name, resize_image)
            worker_thread = threading.Thread(target=uploadFrameAndRequestRecognition, args=(image_name,))
            worker_thread.start()
        if (frame_count / (FRAME_RATE/2)) == NUM_FRAMES:  # exit condition
            writer.release()
            final_video_path = os.path.join(os.getcwd(), finalVideoName)
            s3 = boto3.client("s3", region_name=AWS_REGION)
            s3.upload_file(final_video_path, s3VideoBucket, finalVideoName)
            break
    camera.close()
    
if __name__ == '__main__':
    recordVideo()
