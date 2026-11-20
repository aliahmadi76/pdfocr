# PDF OCR Tool: Overview, Security and Maintenance

Last updated: 2026-11-20

This document explains what the PDF OCR Tool does, how it is built, how it is secured, how it is deployed, and how to change it. Read it before you change or redeploy anything.

## 1. What the app does

FMA staff drop in scanned PDFs (single files or a whole folder). The tool sends each file to Azure AI Document Intelligence, which adds a text layer so the PDF becomes searchable. Users download each result, or all results as a ZIP with a CSV and JSON processing log.

## 2. Components

```text
Browser (app/index.html)
  -> Azure Static Web App   pdfocrvzeotjuko574u-swa      (hosts index.html)
  -> Azure Function App     fn-pdfocr-api                (api/function_app.py)
       -> Azure Storage     pdfocrvzeotjuko574ust        (containers: uploads, outputs)
       -> Document Intelligence (prebuilt-read, searchable PDF output)
  Entra ID (sign-in)
       -> "FMA PDF OCR Tool" app registration  (Static Web App login)
       -> "pdfocr-api" app registration        (Function App token, appId 8c9e2fe0-3dca-4425-b58d-a97e76dbb36e)
```

| Path | Purpose |
|---|---|
| `app/index.html` | The whole front end: HTML, CSS and JavaScript in one file. Uses JSZip and FileSaver from CDN, and MSAL.js for sign-in. |
| `app/staticwebapp.config.json` | Static Web App routing and login rules. Every route requires the `authenticated` role. |
| `api/function_app.py` | Python Azure Functions: `hello`, `upload`, `start-ocr`, `get-ocr-pdf`. |
| `api/host.json`, `api/requirements.txt` | Function runtime settings and Python dependencies. |
| `infra/main.bicep` | Infrastructure template for the storage account, containers, table, Document Intelligence and Static Web App. See section 7. |
| `.github/workflows/swa.yml` | Deploys `app/` to the Static Web App on every push to `main`. |
| `docs/` | Support documentation. This file is the overview. |

## 3. How processing works

For each selected PDF, the browser runs these steps (three files at a time):

1. **Get an upload URL.** `GET /api/upload?filename=<name>` returns a write-only SAS URL for `uploads/<name>`, valid for 1 hour.
2. **Upload the PDF.** The browser PUTs the file straight to Blob Storage using that SAS URL.
3. **Start OCR.** `POST /api/start-ocr` with `{blob_url, filename, job_id}` asks Document Intelligence to analyse the PDF and return a searchable PDF (`output=pdf`). The response is the operation URL.
4. **Poll for the result.** The browser calls `GET /api/get-ocr-pdf` every 2.5 seconds with the operation URL. The function returns the status until it succeeds. It then downloads the PDF, saves it to `outputs/<job_id>/<filename>` and returns a read-only SAS URL, valid for 1 hour.
5. **Show the result.** The browser shows a Download link. **Download All** fetches each result and builds a ZIP that also contains `ocr_processing_log.csv` and `ocr_processing_log.json`.

`job_id` is the timestamp of the run, generated in the browser. It groups each run's outputs into one virtual folder, for example `outputs/2026-11-20T04-00-00-000Z/invoice.pdf`. Blob Storage has no real folders; the `/` is just part of the blob name.

### Function endpoints

| Endpoint | Method | Notes |
|---|---|---|
| `/api/hello` | GET | Health check. Returns `Hello works`. |
| `/api/upload?filename=` | GET | Returns a raw SAS URL, not HTML. |
| `/api/start-ocr` | POST | Body: `blob_url`, `filename`, `job_id`. Returns the operation URL. |
| `/api/get-ocr-pdf?op=&filename=&job_id=` | GET | Returns `status` JSON until done, then a raw SAS URL. |

### Function App settings

These must exist in `fn-pdfocr-api` → Configuration:

- `STORAGE_ACCOUNT_NAME`, `STORAGE_ACCOUNT_KEY`: used to sign SAS URLs.
- `AzureWebJobsStorage`: connection string, used to write outputs.
- `DOCINTEL_ENDPOINT`, `DOCINTEL_KEY`: Document Intelligence.

Do not put these values in git. Export them to a private file if you need a backup.

## 4. Security model (as of 2026-11-20)

| Layer | Control | State |
|---|---|---|
| Storage | Anonymous blob access disabled on the account (`allowBlobPublicAccess = false`). Containers are private. | Done |
| Storage | Browser and function use time-limited SAS URLs only. | Done |
| Frontend (Static Web App) | Built-in Entra login through the "FMA PDF OCR Tool" app registration. `staticwebapp.config.json` requires the `authenticated` role on all routes. | In place (see open item A) |
| Function App | Easy Auth with Entra ID, audience `api://8c9e2fe0-…`. Unauthenticated requests return 401. | Done (open item B) |
| Function App | Only assigned users can get a token ("Assignment required" on `pdfocr-api`, with `App_PdfOCR_Users` assigned). | Done (open item C) |

### Open items

- **A. Two sign-in layers.** The Static Web App login and the MSAL popup both ask the user to sign in. Confirm whether the SWA login is wanted. If yes, the user signs in twice; if not, remove the SWA login rules.
- **B. Enforce Function App sign-in.** Done 2026-11-20: unauthenticated requests return 401. A signed-in user test is still needed.
- **C. Access scope.** Done 2026-11-20: "Assignment required" is on `pdfocr-api` and `FMA PDF OCR Tool`. Assigned to `App_PdfOCR_Users` and Data and Evidence Team.
- **D. Power Apps.** Done 2026-11-21: the Power Apps origin was removed from the storage CORS rules. The API's Function App CORS list no longer includes it either.
- **E. Known weaknesses.** `/api/upload` will sign an upload URL for any filename. The functions use the storage account key rather than managed identity. Document Intelligence and storage keys are plain app settings. Address these in a later change.

## 5. Repository contents to clean up

Before the next push to `main` (which deploys all of `app/`):

- `app/index copy*.html` and `app/index copy before changes.html`: old versions that call the API without a token. They are published with the site, so move them out of the repo.
- `app/staticwebapp.config copy.json` and `api/function_app copy.py`: old copies. Remove.
- `docs/old func.bak`, `api/__pycache__/`: remove, or add to `.gitignore`.
- `api/function_app.py`: has uncommitted changes that were not made by the auth work. Review them before publishing.

## 6. Deploying

### Front end (app/index.html)

Normal path: commit and push to `main`. The `Deploy SWA` workflow uploads `app/` to the Static Web App.

```powershell
cd "C:\Users\ali.ahmadi\OneDrive - fma.govt.nz\Documents\GitHub\pdfocr"
git status
git add app/index.html
git commit -m "Describe the change"
git push origin main
```

Then check the run under the repository's **Actions** tab. Test the app in a browser (hard refresh with Ctrl+F5).

Alternative (if the workflow is unavailable): in the portal open the Static Web App → Overview → Manage deployment token, then run `npx @azure/static-web-apps-cli deploy ./app --deployment-token <token> --env production`. Do not commit the token.

### Back end (api/)

Run the checks, then publish:

```powershell
cd "C:\Users\ali.ahmadi\OneDrive - fma.govt.nz\Documents\GitHub\pdfocr\api"
python -m py_compile function_app.py
func azure functionapp publish fn-pdfocr-api --python --build remote
```

Test:

- `https://fn-pdfocr-api.azurewebsites.net/api/hello` returns `Hello works`.
- `https://fn-pdfocr-api.azurewebsites.net/api/upload?filename=test.pdf` returns a `https://` SAS URL (once auth is enforced, use a signed-in token).

Publishing the back end does not change the front end. Publishing the front end does not change the back end. Keep the two in step when an API change affects `index.html`.

### Infrastructure

`infra/main.bicep` describes the storage account, containers, table, Document Intelligence and Static Web App. It already sets `allowBlobPublicAccess: false`, but the live account had drifted, so **check the live resources before redeploying the template**. Use `az deployment group what-if` to see the changes first.

## 7. Making changes

| Change | Where | How to deploy |
|---|---|---|
| UI text, layout, JavaScript | `app/index.html` | Commit and push to `main` |
| Processing logic, new endpoint | `api/function_app.py` | Compile check, then `func azure functionapp publish` |
| Storage, Document Intelligence, SWA resources | `infra/main.bicep` | `what-if`, then deploy; compare with the live resource first |
| Auth (Function App) | Portal → `fn-pdfocr-api` → Authentication; Entra app `pdfocr-api` | Test with a signed-in user and a request without a token |
| Who can use the app | Enterprise app `pdfocr-api` → Users and groups | No deploy needed |

Good practice:

- Keep a backup branch before risky changes (`git branch <name>`).
- Export Function App settings before changing them.
- Test with a small PDF first, then a folder, then the ZIP download.

## 8. Troubleshooting

| Symptom | Likely cause | Check |
|---|---|---|
| Page reloads and file list disappears when clicking Upload | Sign-in used a full-page redirect | `index.html` should use `loginPopup` |
| Sign-in popup blocked | Browser setting | Allow popups for the site |
| `SAS failed` | Function unreachable, unauthenticated, or missing settings | `/api/hello`, Function App settings, sign-in |
| HTTP 401 from the API | Token missing or expired, or auth enforced | Sign out and back in; check the `pdfocr-api` scope |
| Storage link shows `PublicAccessNotPermitted` (409) for a list request | Expected: anonymous access is off | Use a SAS URL |
| Download link shows raw HTML or a long SAS URL in the UI | Backend returned HTML | Check the `/api/upload` response in the browser network tab |

## 9. Repository and local files

- Local folder: `C:\Users\ali.ahmadi\OneDrive - fma.govt.nz\Documents\GitHub\pdfocr` (synced by OneDrive).
- GitHub: `https://github.com/aliahmadi76/pdfocr`, branch `main`.
- Do not commit: API keys, storage keys, deployment tokens, or exported settings files.
