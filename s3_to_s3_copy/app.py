from typing import List
from dataclasses import dataclass
from datetime import datetime
import boto3

WORD_CHECK = ["captain tsubasa", "star wars"]


@dataclass
class S3File:
    name: str
    timestamp: float
    size_mb: float
    str_found: bool


# set clients for aws resources
s3_client = boto3.resource("s3")
dynamodb_client = boto3.resource("dynamodb")


def contains_str(list_of_words: List[str], obj_name: str) -> bool:
    for word in list_of_words:
        if word in obj_name:
            return True

    return False


def lambda_handler(event, context):
    try:
        s3_event = event["Records"][0]["s3"]
        s3_obj = s3_event["object"]

        copy_source = {"Bucket": s3_event["bucket"]["name"], "Key": s3_obj["key"]}

        bucket = s3_client.Bucket("target-bucket-dyslexicat")

        obj_name = s3_obj["key"]
        size = s3_obj["size"]
        print(obj_name)

        bucket.copy(copy_source, obj_name)

        file = S3File(
            name=obj_name,
            timestamp=datetime.now().timestamp(),
            size_mb=size,
            str_found=contains_str(list_of_words=WORD_CHECK, obj_name=obj_name),
        )

        print(file)
    except Exception as err:
        print(err)
        raise err
