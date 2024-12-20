import json
import logging
import os

import boto3
from botocore.exceptions import ClientError
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response

logger = logging.getLogger(__name__)

root_path = os.environ.get("ROOT_PATH", "/")

app = FastAPI(root_path=root_path)

annotations_bucket = os.environ.get("ANNOTATIONS_BUCKET", "")


def key_to_json(key: str, request: Request) -> json:
    """Converts AWS keys to a dictionary with the file name and its URL"""

    base_url = str(request.base_url).rstrip("/")

    url = f"{base_url}/{key}"

    return {"file": key.split("/")[-1], "href": url}


def bucket_contents_to_json(contents: dict, path: str, request: Request) -> json:
    """Returns the contents of the bucket in JSON format with links provided for access to the
    individual files"""
    links = {"path": path, "links": []}
    for entry in contents.get("Contents"):

        key = entry["Key"]
        key_entry = key_to_json(key, request)

        links["links"].append(key_entry)

    return links


@app.get("/catalogue/{path}/annotations")
async def get_all_annotations(path: str, request: Request):
    """Collects all available annotations at a given path"""
    s3 = boto3.client("s3")
    result = s3.list_objects(Bucket=annotations_bucket, Prefix=f"catalogue/{path}/annotations")
    return bucket_contents_to_json(result, path, request)


@app.get("/catalogue/{path}/annotations/{uuid}", response_class=Response)
async def get_specific_annotation(path: str, uuid: str, request: Request):
    """Returns annotation at a given path. Attempts to retrieve the file directly given by the URL if it
    exists. If it doesn't, it checks the header for a file type. If no file type exists, assume .ttl and
    try to retrieve file of given file type"""
    file_type = (
        request.headers.get("accept") if "*/*" not in request.headers.get("accept") else None
    )

    s3 = boto3.client("s3")

    file_name = f"{uuid}.{file_type}" if file_type else uuid

    key = f"catalogue/{path}/annotations/{file_name}"

    try:
        data = s3.get_object(Bucket=annotations_bucket, Key=key)

    except ClientError:
        try:
            data = s3.get_object(Bucket=annotations_bucket, Key=f"{key}.ttl")
            file_name = f"{file_name}.ttl"

        except ClientError:
            logging.warning(f"Key {key} not found")
            raise HTTPException(
                status_code=415,
                detail=f"Key {key} not found. Have you included a valid file type in the header? "
                f"e.g. `Accept: ttl`",
            ) from None

    return Response(
        content=data["Body"].read(),
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment;filename={file_name}"},
    )
