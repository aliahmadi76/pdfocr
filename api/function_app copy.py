import os
from datetime import datetime, timedelta

import azure.functions as func
import requests   # ✅ add only now
from azure.storage.blob import generate_blob_sas, BlobSasPermissions

app = func.FunctionApp()

@app.function_name(name="hello")
@app.route(route="hello", auth_level=func.AuthLevel.ANONYMOUS)
def hello(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse("Hello works")

@app.function_name(name="upload")
@app.route(route="upload", auth_level=func.AuthLevel.ANONYMOUS)
def upload(req: func.HttpRequest) -> func.HttpResponse:
    filename = req.params.get("filename")

    if not filename:
        return func.HttpResponse("Missing filename", status_code=400)

    account_name = os.environ.get("STORAGE_ACCOUNT_NAME")
    account_key = os.environ.get("STORAGE_ACCOUNT_KEY")

    sas = generate_blob_sas(
        account_name=account_name,
        container_name="uploads",
        blob_name=filename,
        account_key=account_key,
        permission=BlobSasPermissions(read=True, write=True),
        expiry=datetime.utcnow() + timedelta(hours=1)
    )

    url = f"https://{account_name}.blob.core.windows.net/uploads/{filename}?{sas}"
    return func.HttpResponse(url)

@app.function_name(name="start_ocr")
@app.route(route="start-ocr", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def start_ocr(req: func.HttpRequest) -> func.HttpResponse:
    data = req.get_json()
    blob_url = data.get("blob_url", "").strip()

    endpoint = os.environ["DOCINTEL_ENDPOINT"].rstrip("/")
    key = os.environ["DOCINTEL_KEY"]

    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": "application/json"
    }

    analyze_url = f"{endpoint}/documentintelligence/documentModels/prebuilt-read:analyze?api-version=2024-11-30&output=pdf"

    resp = requests.post(
        analyze_url,
        headers=headers,
        json={"urlSource": blob_url}
    )

    op = resp.headers.get("operation-location", "")
    return func.HttpResponse(op)
@app.function_name(name="get_ocr_pdf")
@app.route(route="get-ocr-pdf", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def get_ocr_pdf(req: func.HttpRequest) -> func.HttpResponse:

    import requests
    import json
    import re
    from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
    from datetime import datetime, timedelta

    op = req.params.get("op")
    if not op:
        return func.HttpResponse("Missing op", status_code=400)

    endpoint = os.environ["DOCINTEL_ENDPOINT"].rstrip("/")
    key = os.environ["DOCINTEL_KEY"]

    headers = {
        "Ocp-Apim-Subscription-Key": key
    }

    # ✅ check status
    status_resp = requests.get(op, headers=headers)
    status = status_resp.json().get("status")

    if status != "succeeded":
        return func.HttpResponse(status_resp.text, mimetype="application/json")

    # ✅ extract resultId
    match = re.search(r"/analyzeResults/([0-9a-fA-F-]+)", op)
    if not match:
        return func.HttpResponse("Invalid op", status_code=500)

    result_id = match.group(1)

    # ✅ download PDF
    pdf_url = f"{endpoint}/documentintelligence/documentModels/prebuilt-read/analyzeResults/{result_id}/pdf?api-version=2024-11-30"
    pdf_resp = requests.get(pdf_url, headers=headers)

    if pdf_resp.status_code != 200:
        return func.HttpResponse("Failed to fetch PDF", status_code=500)

    # ✅ save to blob
    blob_service = BlobServiceClient.from_connection_string(os.environ["AzureWebJobsStorage"])

    container = "outputs"
    filename = f"{result_id}.pdf"

    blob_client = blob_service.get_blob_client(container=container, blob=filename)
    blob_client.upload_blob(pdf_resp.content, overwrite=True)

    # ✅ SAS link
    sas = generate_blob_sas(
        account_name=os.environ["STORAGE_ACCOUNT_NAME"],
        container_name=container,
        blob_name=filename,
        account_key=os.environ["STORAGE_ACCOUNT_KEY"],
        permission=BlobSasPermissions(read=True),
        expiry=datetime.utcnow() + timedelta(hours=1)
    )

    url = f"https://{os.environ['STORAGE_ACCOUNT_NAME']}.blob.core.windows.net/{container}/{filename}?{sas}"

    return func.HttpResponse(url)