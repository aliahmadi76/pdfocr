import azure.functions as func
import os
import requests
from azure.storage.blob import BlobService(http_auth_level=func.AuthLevel.ANONYMOUS)from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions

STORAGE_ACCOUNT_NAME = os.environ.get("STORAGE_ACCOUNT_NAME")
STORAGE_CONNECTION = os.environ.get("AzureWebJobsStorage")
UPLOAD_CONTAINER = "uploads"

# ✅ 1. Generate upload SAS
@app.function_name(name="upload")
@app.route(route="upload")
def upload(req: func.HttpRequest) -> func.HttpResponse:
    filename = req.params.get("filename")

    sas = generate_blob_sas(
        account_name=STORAGE_ACCOUNT_NAME,
        container_name=UPLOAD_CONTAINER,
        blob_name=filename,
        permission=BlobSasPermissions(write=True),
        expiry=datetime.utcnow() + timedelta(hours=1),
        account_key=None
    )

    url = f"https://{STORAGE_ACCOUNT_NAME}.blob.core.windows.net/{UPLOAD_CONTAINER}/{filename}?{sas}"

    return func.HttpResponse(url)


# ✅ 2. Start OCR
@app.function_name(name="start_ocr")
@app.route(route="start-ocr", methods=["POST"])
def start_ocr(req: func.HttpRequest) -> func.HttpResponse:
    data = req.get_json()
    blob_url = data.get("blob_url")

    endpoint = os.environ.get("DOCINTEL_ENDPOINT")
    key = os.environ.get("DOCINTEL_KEY")

    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": "application/json"
    }

    body = {
        "urlSource": blob_url
    }

    resp = requests.post(
        f"{endpoint}/formrecognizer/documentModels/prebuilt-read:analyze?api-version=2023-07-31",
        headers=headers,
        json=body
    )

    return func.HttpResponse(resp.headers.get("operation-location"))


# ✅ 3. Check OCR status
@app.function_name(name="status")
@app.route(route="status")
def status(req: func.HttpRequest) -> func.HttpResponse:
    url = req.params.get("url")

    endpoint_key = os.environ.get("DOCINTEL_KEY")

    headers = {
        "Ocp-Apim-Subscription-Key": endpoint_key
    }

    resp = requests.get(url, headers=headers)

    return func.HttpResponse(resp.text, mimetype="application/json")
from datetime import datetime, timedelta

