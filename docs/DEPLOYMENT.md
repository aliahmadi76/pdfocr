# PDF OCR Tool – Deployment and Support Guide

## Purpose

This guide documents how the PDF OCR Tool is deployed and supported. It is intended for FMA Technical Operations team members who may need to maintain the application after the original implementation work.

The application has two main components:

1. **Front-end:** `index.html`, deployed through Git/GitHub to the Azure Static Web App.
2. **Back-end:** `function_app.py`, deployed directly from VS Code/PowerShell to the Azure Function App using Azure Functions Core Tools.

## High-Level Architecture

```text
User browser
  -> Azure Static Web App, index.html
  -> Azure Function App, function_app.py
  -> Azure AI Document Intelligence
  -> Azure Blob Storage
```

Blob containers used by the application:

```text
uploads   - temporary/input PDFs uploaded by the browser
outputs   - OCR output PDFs and future batch/job folders
```

## Repository and Local Paths

Typical local repository path:

```powershell
C:\Users\ali.ahmadi\OneDrive - fma.govt.nz\Documents\GitHub\pdfocr
```

Typical API folder path:

```powershell
C:\Users\ali.ahmadi\OneDrive - fma.govt.nz\Documents\GitHub\pdfocr\api
```

Expected API folder contents:

```text
api/
  function_app.py
  host.json
  requirements.txt
```

## Front-End Deployment: index.html Through Git

The front-end is deployed through Git. Changes to `index.html` should be committed and pushed to the repository. The Azure Static Web App deployment should then be triggered by the repository workflow.

### Step 1: Go to the repo root

```powershell
cd "C:\Users\ali.ahmadi\OneDrive - fma.govt.nz\Documents\GitHub\pdfocr"
```

### Step 2: Confirm changed files

```powershell
git status
```

Confirm that `index.html` or the expected front-end file path is listed as modified.

If `git add index.html` fails with `pathspec 'index.html' did not match any files`, locate the file:

```powershell
Get-ChildItem -Recurse -Filter index.html
```

Then add the returned path, or use:

```powershell
git add .
```

### Step 3: Commit changes

```powershell
git add .
git commit -m "Update PDF OCR front-end"
```

Use a more specific commit message when possible, for example:

```powershell
git commit -m "Add OCR processing logs and batch job id support"
```

### Step 4: Push changes

```powershell
git push origin main
```

If the branch is not `main`, check the current branch:

```powershell
git branch
```

Push to the branch marked with `*` if that is the deployment branch.

### Step 5: Verify Static Web App deployment

Check the GitHub Actions workflow for the repository and confirm the Static Web App deployment completed successfully.

## Back-End Deployment: function_app.py Directly From VS Code/PowerShell

The Azure Function App is deployed directly from the API folder using Azure Functions Core Tools.

### Step 1: Open the API folder

```powershell
cd "C:\Users\ali.ahmadi\OneDrive - fma.govt.nz\Documents\GitHub\pdfocr\api"
```

Confirm the folder contains:

```powershell
dir
```

Expected files:

```text
function_app.py
host.json
requirements.txt
```

### Step 2: Validate Python syntax before deploying

Always run this before publishing:

```powershell
python -m py_compile function_app.py
```

Expected result:

```text
No output
```

If a syntax or indentation error appears, fix the file before publishing.

### Step 3: Check for accidental HTML copied into Python

The Function App must return raw URL strings, not HTML anchor tags. Run:

```powershell
findstr /i "<a href" function_app.py
```

Expected result:

```text
No output
```

If this command returns any line, remove the HTML. The backend should return only plain URLs, for example:

```python
return func.HttpResponse(url)
```

where `url` begins with `https://`.

### Step 4: Identify the real Azure Function App name

If a publish command fails with `Can't find app with name`, list available Function Apps:

```powershell
az login
az account show
az functionapp list --query "[].name" -o table
```

Use the exact Function App name returned by Azure.

### Step 5: Publish the Function App

From the `api` folder:

```powershell
func azure functionapp publish <FUNCTION_APP_NAME> --python --build remote
```

Example:

```powershell
func azure functionapp publish pdfocr-api-prod --python --build remote
```

Do not assume the Function App name is the same as the URL or previous examples. Confirm it with Azure if unsure.

### Step 6: Verify the Function App

Test the health endpoint:

```text
https://<FUNCTION_APP_NAME>.azurewebsites.net/api/hello
```

Expected response:

```text
Hello works
```

Test SAS generation:

```text
https://<FUNCTION_APP_NAME>.azurewebsites.net/api/upload?filename=test.pdf
```

Expected response:

```text
A raw Azure Blob SAS URL beginning with https://
```

It should not return HTML.

## Important Implementation Notes

### index.html generates the user-facing download link

The front-end receives a raw URL from the backend and creates the clickable link in JavaScript. The backend should not return HTML.

Correct front-end pattern:

```javascript
setStatus(
  item,
  "done",
  '<a href="' + downloadUrl + '" target="_blank">📥 Download</a>'
);
```

### Backend returns raw URLs only

Correct Python pattern in `upload()`:

```python
url = (
    f"https://{account_name}"
    f".blob.core.windows.net/uploads/"
    f"{filename}?{sas}"
)

return func.HttpResponse(url)
```

Correct Python pattern in `get_ocr_pdf()`:

```python
url = (
    f"https://{os.environ['STORAGE_ACCOUNT_NAME']}"
    f".blob.core.windows.net/{container}/{blob_name}?{sas}"
)

return func.HttpResponse(url)
```

### Batch folder support

The front-end generates a batch/job ID and passes it to the backend. The backend uses that value as part of the blob name:

```python
if job_id:
    blob_name = f"{job_id}/{filename}"
else:
    blob_name = filename
```

This creates an Azure Blob virtual folder structure like:

```text
outputs/
  2026-07-20T10-00-00-000Z/
    invoice.pdf
    contract.pdf
```

Azure Blob Storage does not create physical folders. It uses `/` in blob names to present a folder-like hierarchy.

## Support Checklist Before Any Deployment

- [ ] Confirm the correct repo/folder is open.
- [ ] Save all code changes in VS Code.
- [ ] Run `git status`.
- [ ] Run `python -m py_compile function_app.py` from the API folder.
- [ ] Run `findstr /i "<a href" function_app.py` and confirm there is no output.
- [ ] Confirm `const BASE` in `index.html` is a plain URL string.
- [ ] Commit front-end changes to Git.
- [ ] Push front-end changes to the deployment branch.
- [ ] Publish the Function App from the `api` folder.
- [ ] Test `/api/hello`.
- [ ] Test `/api/upload?filename=test.pdf`.
- [ ] Upload a small test PDF through the UI.
- [ ] Confirm the output PDF appears under the expected `outputs/<job_id>/` path.
- [ ] Confirm individual download links work.
- [ ] Confirm Download All ZIP works.
- [ ] Confirm `ocr_processing_log.csv` and `ocr_processing_log.json` appear in the ZIP.

## Common Issues and Fixes

### Issue: SAS failed

Meaning: the browser failed at this stage:

```javascript
const sasResp = await fetch(`${BASE}/api/upload?filename=${encodeURIComponent(safe)}`);
```

Check:

1. `const BASE` in `index.html` is a plain Function App URL.
2. `/api/hello` works.
3. `/api/upload?filename=test.pdf` returns a raw SAS URL.
4. `function_app.py` compiles.
5. Required Function App settings exist:
   - `STORAGE_ACCOUNT_NAME`
   - `STORAGE_ACCOUNT_KEY`
   - `AzureWebJobsStorage`
   - `DOCINTEL_ENDPOINT`
   - `DOCINTEL_KEY`

### Issue: Blob output still appears as filename_ocr.pdf

Meaning: the deployed Function App is probably still running old code. Search local code:

```powershell
findstr /s /i "_ocr.pdf" *.py
```

If the local code no longer contains `_ocr.pdf`, deploy the Function App again and verify the real Function App name.

### Issue: Download link shows a long SAS URL in the UI

Meaning: the front-end link HTML is malformed, or the backend returned HTML instead of a raw URL.

The backend should return a raw URL only. The front-end should create the anchor tag.

### Issue: Python compile fails with IndentationError

Run:

```powershell
python -m py_compile function_app.py
```

Fix the line number reported. Common causes are extra spaces before `if`, mixed tabs/spaces, or copied HTML fragments.

## Recommended Repository Support Files

Suggested files to add under the repo:

```text
docs/
  DEPLOYMENT.md
  FUNCTION_APP_DEPLOYMENT.md
  TROUBLESHOOTING.md
  SUPPORT_CHECKLIST.md
  ARCHITECTURE.md
```

Suggested root file:

```text
README.md
```

The `README.md` should link to the docs folder and describe the app at a high level.
