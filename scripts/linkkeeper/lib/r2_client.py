"""Cloudflare R2 (S3-compatible) upload client for WARC snapshots."""

import logging

import boto3
from botocore.config import Config as BotoConfig

logger = logging.getLogger("linkkeeper.r2")


def get_r2_client(config):
    """Create a boto3 S3 client configured for Cloudflare R2."""
    return boto3.client(
        "s3",
        endpoint_url=config["r2_endpoint"],
        aws_access_key_id=config["r2_access_key"],
        aws_secret_access_key=config["r2_secret_key"],
        config=BotoConfig(
            signature_version="s3v4",
            retries={"max_attempts": 3, "mode": "standard"},
        ),
        region_name="auto",
    )


def upload_warc(client, bucket, key, file_path):
    """Upload a WARC file to R2.

    Returns dict with:
        success: bool
        size: file size in bytes
        error: error message if failed
    """
    import os

    result = {"success": False, "size": 0, "error": None}

    try:
        file_size = os.path.getsize(file_path)
        client.upload_file(
            file_path,
            bucket,
            key,
            ExtraArgs={"ContentType": "application/warc"},
        )
        result["success"] = True
        result["size"] = file_size
        logger.info("Uploaded %s (%d bytes) to r2://%s/%s", file_path, file_size, bucket, key)
    except Exception as e:
        result["error"] = str(e)
        logger.error("R2 upload failed for %s: %s", key, e)

    return result


def list_warcs(client, bucket, prefix="warcs/"):
    """List WARC files in the R2 bucket."""
    try:
        paginator = client.get_paginator("list_objects_v2")
        keys = []
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                keys.append({
                    "key": obj["Key"],
                    "size": obj["Size"],
                    "modified": obj["LastModified"].isoformat(),
                })
        return keys
    except Exception as e:
        logger.error("R2 list failed: %s", e)
        return []
