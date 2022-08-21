from typing import List
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from urllib.parse import unquote_plus
import uuid
import boto3

WORD_CHECK = ["captain tsubasa", "star wars"]
TARGET_BUCKET_NAME = "target-bucket-dyslexicat-test"
TABLE_NAME = "FileMetadataInfo"


@dataclass
class S3File:
    id: str
    name: str
    timestamp: int
    size_mb: Decimal
    str_found: bool


def conv_byte_to_mb(size: int) -> Decimal:
    return round(Decimal(size * (1 / 100000)), 6)


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
        obj_name = unquote_plus(s3_obj["key"])

        copy_source = {"Bucket": s3_event["bucket"]["name"], "Key": obj_name}

        bucket = s3_client.Bucket(TARGET_BUCKET_NAME)

        size = conv_byte_to_mb(s3_obj["size"])

        print(s3_obj)
        print(obj_name)

        bucket.copy(copy_source, obj_name)

        table = dynamodb_client.Table(TABLE_NAME)

        file = S3File(
            id=str(uuid.uuid4()),
            name=obj_name,
            # dynamodb does not support float
            timestamp=int(datetime.now().timestamp()),
            size_mb=size,
            str_found=contains_str(list_of_words=WORD_CHECK, obj_name=obj_name),
        )

        print(file)
        table.put_item(
            Item={
                "id": file.id,
                "name": file.name,
                "timestamp": file.timestamp,
                "size_mb": file.size_mb,
                "found": file.str_found,
            }
        )

    except Exception as err:
        print(err)
        raise err
