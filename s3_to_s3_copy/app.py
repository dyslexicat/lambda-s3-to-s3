from typing import List
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from urllib.parse import unquote_plus
import uuid
import logging
import boto3
import os

# an array of phrases that will be used to check whether the name contains them or not
PHRASE_CHECKLIST = ["captain tsubasa", "star wars"]
# the name of the target bucket that s3 objects will be copied to
TARGET_BUCKET_NAME = os.getenv("TARGET_BUCKET_NAME")
# the name of the dynamodb table
TABLE_NAME = os.getenv("TABLE_NAME")
# log level that will be used throughout
LOG_LEVEL = logging.DEBUG if os.getenv("DEBUG", False) else logging.INFO

logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)

# S3File class contains the metadata information about the object uploaded to S3
@dataclass
class S3File:
    id: str
    name: str
    timestamp: int
    size_mb: Decimal
    str_found: bool

    def write_metadata(self, table):
        table.put_item(
            Item={
                "id": self.id,
                "name": self.name,
                "timestamp": self.timestamp,
                "size_mb": self.size_mb,
                "found": self.str_found,
            }
        )


# conversion between bytes to megabytes since uploaded objects have their size as bytes
def conv_byte_to_mb(size: int) -> Decimal:
    return round(Decimal(size * (1 / 100000)), 6)


# set clients for aws resources
s3_client = boto3.resource("s3")
dynamodb_client = boto3.resource("dynamodb")


# function that checks whether the object name includes one of the phrases in our checklist
def contains_str(list_of_phrases: List[str], obj_name: str) -> bool:
    for word in list_of_phrases:
        if word in obj_name:
            return True

    return False


def lambda_handler(event, context):
    try:
        s3_event = event["Records"][0]["s3"]
        s3_obj = s3_event["object"]
        # unquote the object name since aws encodes spaces in filenames as +
        obj_name = unquote_plus(s3_obj["key"])

        copy_source = {"Bucket": s3_event["bucket"]["name"], "Key": obj_name}

        bucket = s3_client.Bucket(TARGET_BUCKET_NAME)

        size = conv_byte_to_mb(s3_obj["size"])

        logger.info(f"Copying {obj_name} to the {TARGET_BUCKET_NAME} bucket")

        bucket.copy(copy_source, obj_name)

        table = dynamodb_client.Table(TABLE_NAME)

        file = S3File(
            id=str(uuid.uuid4()),
            name=obj_name,
            # dynamodb does not support float
            timestamp=int(datetime.now().timestamp()),
            size_mb=size,
            str_found=contains_str(list_of_phrases=PHRASE_CHECKLIST, obj_name=obj_name),
        )

        logger.info(f"Writing {file} to the {TABLE_NAME} DynamoDB table")
        file.write_metadata(table)

    except Exception as err:
        logger.error(err)
        raise err
