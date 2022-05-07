import time
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
VIDEO_FORMAT = '.mp4'
IMAGE_FORMAT = '.png'
NUM_FRAMES = 600  # 5 minutes video == 600 frames @ 2 frames/sec.
MAX_WORKERS = 1
AWS_REGION = "us-east-1"
s3InputBucket = "g45-frame-extraction-bucket"
s3outputBucket = "g45-output-bucket"

faceRecognitionApiUrl = "https://enwpn2jcw4.execute-api.us-east-1.amazonaws.com/faceRec/facerecogition"


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
    return result


def sendGetRecognitionRequest(request):
    headers = {"Content-Type": "application/json"}
    start_timestamp = datetime.now()
    print("Sending Get request to lambda")
    http_response = requests.get(url=faceRecognitionApiUrl, params=request, headers=headers)
    end_time = datetime.now()
    latency = end_time - start_timestamp
    print("latency: " + str(latency.total_seconds()) + " seconds")
    print(http_response.text)


def uploadFrameAndRequestRecognition(image_name):
    print("Upload function started in threadid: " + str(threading.get_ident()))
    response = uploadFrame(image_name)
    if response:
        request = {
            "ImageName": image_name,
            "BucketName": "g45-frame-extraction-bucket"
        }
        sendGetRecognitionRequest(request)
        try:
            os.remove(os.path.join(os.getcwd(), image_name))
            print("Local file deleted!")
        except OSError as e:
            if e.errno != errno.ENOENT:
                print("File does not exist, so ignoring deletion")
            else:
                print("Error in deleting " + image_name + " file")
    return response


def recordVideo():
    camera = PiCamera()
    camera.resolution = (160, 160);
    camera.framerate = 30
    capture_object = PiRGBArray(camera, size=(160, 160))
    time.sleep(0.1)  # For the camera to get setup.
    # Initialising the opencv video writer object.
    video_path = os.path.join(os.getcwd(), "finalDemoVideo.mp4")
    w, h = (160, 160)
    fourcc = cv2.VideoWriter_fourcc('m', 'p', '4', 'v')
    fps = 30
    writer = cv2.VideoWriter(video_path, fourcc, fps, (w, h))
    frame_count = 0
    bucket_params = {'name': s3InputBucket, 'region': AWS_REGION}
    # A one time check to make sure the input bucket exists in the AWS.
    # If it doesn't exist, the below API call will create one.
    getS3Bucket(bucket_params)
    # Initialising Thread pool Executor
    # executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
    results = []
    timestamp = 0
    for frame in camera.capture_continuous(capture_object, format='rgb', use_video_port=True):
        frame_count = frame_count + 1
        image = frame.array
        # The image is saved into the output video file.
        writer.write(image)
        #timestamp = datetime.now()
        #timestamp = timestamp.strftime("%d_%m_%Y_%H_%M_%S")
        timestamp = timestamp + 1
        image_name = str(timestamp) + IMAGE_FORMAT
        cv2.imwrite(image_name, image)
        capture_object.truncate(0)
        # Upload one frame in every 15 frames. (0.5 seconds)
        if frame_count % 15 == 0:
            worker_thread = threading.Thread(target=uploadFrameAndRequestRecognition, args=(image_name,))
            worker_thread.start()
        if (frame_count / 15) == 15:  # exit condition
            break


if __name__ == '__main__':
    # image_name = '06_05_2022_18_30_00.png'
    # request = {
    #     "ImageName": image_name,
    #     "BucketName": "g45-frame-extraction-bucket"
    # }
    # sendGetRecognitionRequest(request)
    recordVideo()
