"""WARC file generation for local snapshots of critical pages."""

import io
import os
import tempfile
import logging
from datetime import datetime, timezone

import requests
from warcio.warcwriter import WARCWriter
from warcio.statusandheaders import StatusAndHeaders

logger = logging.getLogger("linkkeeper.warc")

USER_AGENT = (
    "LinkKeeper/1.0 (https://flowarts.wiki; link preservation bot) "
    "Mozilla/5.0 (compatible)"
)


def capture_url_to_warc(url, output_dir=None):
    """Fetch a URL and write it to a WARC file.

    Returns dict with:
        success: bool
        path: path to WARC file
        size: file size in bytes
        error: error message if failed
    """
    result = {"success": False, "path": None, "size": 0, "error": None}

    if output_dir is None:
        output_dir = tempfile.gettempdir()

    os.makedirs(output_dir, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    safe_url = url.replace("://", "_").replace("/", "_")[:80]
    filename = f"linkkeeper-{safe_url}-{ts}.warc.gz"
    filepath = os.path.join(output_dir, filename)

    try:
        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=30,
            stream=True,
        )

        with open(filepath, "wb") as fh:
            writer = WARCWriter(fh, gzip=True)

            # Write warcinfo record
            info_payload = (
                f"software: LinkKeeper/1.0\r\n"
                f"description: Flow Arts Wiki link preservation snapshot\r\n"
                f"operator: flowarts.wiki\r\n"
            ).encode("utf-8")
            info_record = writer.create_warc_record(
                uri=None,
                record_type="warcinfo",
                warc_content_type="application/warc-fields",
                payload=io.BytesIO(info_payload),
                length=len(info_payload),
            )
            writer.write_record(info_record)

            # Build HTTP status line and headers
            status_line = f"{resp.status_code} {resp.reason}"
            headers_list = list(resp.headers.items())
            http_headers = StatusAndHeaders(
                status_line, headers_list, protocol="HTTP/1.1"
            )

            # Read full response body
            body = resp.content
            payload_stream = io.BytesIO(body)

            # Write response record
            response_record = writer.create_warc_record(
                uri=url,
                record_type="response",
                http_headers=http_headers,
                payload=payload_stream,
                length=len(body),
            )
            writer.write_record(response_record)

        result["success"] = True
        result["path"] = filepath
        result["size"] = os.path.getsize(filepath)
        logger.info("WARC captured: %s -> %s (%d bytes)", url, filepath, result["size"])

    except requests.RequestException as e:
        result["error"] = f"HTTP error: {e}"
        logger.error("WARC capture failed for %s: %s", url, e)
    except Exception as e:
        result["error"] = str(e)
        logger.error("WARC write failed for %s: %s", url, e)

    return result
