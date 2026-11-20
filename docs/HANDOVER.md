# PDF OCR Tool: Handover and Project Guide

Last updated: 2026-11-21

This is the entry point for anyone who supports, changes or redeploys the PDF OCR Tool. It describes the whole project and its Azure resources, and explains how to run, secure, deploy and recover it. The other files in `docs/` cover detail. Where they disagree with this file, this file is current.

## 1. Purpose

FMA staff upload scanned PDFs (single files or a folder). Azure AI Document Intelligence adds a searchable text layer. Users download each result, or all results as a ZIP with a CSV and JSON processing log.

## 2. Architecture

```text
Staff browser (app/index.html, MSAL.js sign-in)
  |-- Entra ID sign-in ("FMA PDF OCR Tool" app, Static Web App login)
  |-- Static Web App  pdfocrvzeotjuko574u-swa   (serves app/)
  |-- Function App    fn-pdfocr-api             (api/function_app.py, Python 3.11)
  |     |-- Entra token check ("pdfocr-api" app, Easy Auth)
  |     |-- Blob Storage pdfocrvzeotjuko574ust  (containers: uploads, outputs)
  |     |-- Document Intelligence pdfocrvzeotjuko574u-docint (prebuilt-read, searchable PDF)
  |-- Browser PUTs PDFs and downloads results directly from Blob Storage using SAS URLs
```

The browser uploads files straight to Blob Storage, so the storage account's CORS rules must allow the Static Web App origin. Without that, uploads fail with "Failed to fetch" even when sign-in works.

## 3. Azure resources

Resource group: `rg-pdf-ocr` (subscription as set in your `az account`).

| Resource | Name | Region | SKU / type | Purpose |
|---|---|---|---|---|
| Static Web App | `pdfocrvzeotjuko574u-swa` | East Asia | Standard | Hosts `app/`. Built-in Entra login. Deploys from `main`. Default host `kind-water-05d731200.7.azurestaticapps.net`. |
| Function App | `fn-pdfocr-api` | Australia East | Linux, Consumption (Y1), Python 3.11 | API: upload SAS, start OCR, poll and fetch results. HTTPS only. Unauthenticated calls return 401. |
| App Service plan | `AustraliaEastLinuxDynamicPlan` | Australia East | Y1 Dynamic | Hosts the Function App. |
| Storage account | `pdfocrvzeotjuko574ust` | Australia East | StorageV2 | Containers `uploads` (input PDFs) and `outputs` (results). Anonymous access disabled. |
| Document Intelligence | `pdfocrvzeotjuko574u-docint` | Australia East | FormRecognizer S0 | OCR. Billed per page. |
| Application Insights | connected through `APPLICATIONINSIGHTS_CONNECTION_STRING` | | | Function logs. |

Entra ID app registrations:

| Name | Client ID | Used for |
|---|---|---|
| `FMA PDF OCR Tool` | `cb4c6631-d76d-43d2-996c-bbbfd8edb787` | Static Web App built-in login (`AZURE_CLIENT_ID`). Has a client secret (`AZURE_CLIENT_SECRET`). |
| `pdfocr-api` | `8c9e2fe0-3dca-4425-b58d-a97e76dbb36e` | Function App audience (`api://8c9e2fe0-…`) and the SPA client MSAL uses to get tokens for the `user_impersonation` scope. |

Access is controlled by assignment. Both apps have "Assignment required" turned on. Assigned: `App_PdfOCR_Users` and the Data and Evidence Team group. Data and Evidence Team is nested in `App_PdfOCR_Users`, but Entra does not pass nested group membership through to app assignments, so it is assigned directly too. New users must be added to `App_PdfOCR_Users` (or assigned to both apps).

### Settings (names only; values are secrets)

Function App `fn-pdfocr-api` → Configuration:

- `STORAGE_ACCOUNT_NAME`: storage account name. Blob access and SAS signing use the Function App's managed identity, so no storage key is stored for the app.
- `AzureWebJobsStorage`: storage connection string for the Functions host and output writes.
- `DOCINTEL_ENDPOINT`, `DOCINTEL_KEY`: Document Intelligence.
- `APPLICATIONINSIGHTS_CONNECTION_STRING`, `FUNCTIONS_WORKER_RUNTIME`, `FUNCTIONS_EXTENSION_VERSION`, `AzureWebJobsFeatureFlags`: runtime.

Static Web App `pdfocrvzeotjuko574u-swa` → Environment variables (default environment):

- `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`: built-in login.
- `STORAGE_ACCOUNT_NAME`, `UPLOAD_CONTAINER`, `OUTPUT_CONTAINER`, `TABLE_NAME`, `AzureWebJobsStorage`, `DOCINTEL_ENDPOINT`, `DOCINTEL_KEY`, `FUNCTIONS_WORKER_RUNTIME`: copies kept on the SWA. Keep them in step with the Function App when keys change.

Storage account lifecycle rule: `Delete older than 48 from upload and output` (on `uploads/` and `outputs/`, delete when last modified is more than 2 days ago). The name says 48 hours, but the rule works in whole days, so the effective window is about 2 to 3 days. Rules run about once a day, so files can persist longer. Do not rely on it for legal or retention purposes.

## 4. Processing flow

For each selected PDF, the browser runs three files at a time:

1. `GET /api/upload?filename=<name>` returns a write-only SAS URL for `uploads/<name>` (1 hour).
2. The browser PUTs the file to that URL.
3. `POST /api/start-ocr` with `{blob_url, filename, job_id}` starts Document Intelligence (`output=pdf`) and returns the operation URL.
4. `GET /api/get-ocr-pdf?op=&filename=&job_id=` is polled every 2.5 seconds. When done, the function saves `outputs/<job_id>/<filename>` and returns a read-only SAS URL (1 hour).
5. **Download All** fetches each result and builds a ZIP with `ocr_processing_log.csv` and `ocr_processing_log.json`.

`job_id` is a timestamp generated in the browser. It groups one run's outputs into a virtual folder. Blob Storage has no real folders.

Endpoints: `/api/hello` (health, returns `Hello works`), `/api/upload`, `/api/start-ocr`, `/api/get-ocr-pdf`.

## 5. Repository layout

| Path | Purpose |
|---|---|
| `app/index.html` | Whole front end (HTML, CSS, JavaScript). JSZip and FileSaver from CDN. |
| `app/redirect.html` | Landing page for the popup sign-in flow. |
| `app/staticwebapp.config.json` | Routes. `/redirect.html` is anonymous. Everything else requires the `authenticated` role. |
| `api/function_app.py`, `api/host.json`, `api/requirements.txt` | Function App code and config. |
| `infra/main.bicep` | Infrastructure template. See section 9 before using it. |
| `.github/workflows/swa.yml` | Deploys `app/` to the Static Web App on every push to `main`. |
| `docs/` | Documentation. |

Clean-up status: the old copies have been removed from the working tree and git (`api/function_app copy.py`, `docs/old func.bak`). `api/__pycache__/` is a local build folder and should be added to `.gitignore`.

## 6. Deploying the Static Web App (front end)

### Current method: GitHub Actions

Push to `main`. The `Deploy SWA` workflow uploads `app/` to the Static Web App. Check the **Actions** tab, then test in a browser with a hard refresh (Ctrl+F5).

```powershell
cd "C:\Users\ali.ahmadi\OneDrive - fma.govt.nz\Documents\GitHub\pdfocr"
git status
git add app
git commit -m "Describe the change"
git push origin main
```

The workflow authenticates with the repository secret `AZURE_STATIC_WEB_APPS_API_TOKEN`. If that token is rotated in Azure, update the secret in GitHub too.

### Alternative methods, if the workflow cannot be used

**A. Deploy from the Azure CLI with the SWA CLI and a deployment token (no GitHub needed).**

```powershell
$token = az staticwebapp secrets list -n pdfocrvzeotjuko574u-swa -g rg-pdf-ocr --query "properties.apiKey" -o tsv
npx @azure/static-web-apps-cli deploy ./app --deployment-token $token --env production
Remove-Variable token
```

Never print or commit the token. The token is equivalent to a deploy password.

**B. Deploy from a different repository or branch.** Change the repository connection on the SWA, or create a new SWA that points at another repository:

```powershell
az staticwebapp create -n <new-name> -g rg-pdf-ocr -s https://github.com/<owner>/<repo> -b <branch> --app-location app --api-location "" --output-location "" --login-with-github
```

If you create a new SWA, you must also:

1. Add its hostname as a redirect URI on the `FMA PDF OCR Tool` app registration (Authentication → Single-page / Web).
2. Set `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET` and the storage/Document Intelligence settings on the new SWA.
3. Add its origin to the storage account CORS rules (Blob service → CORS) with HEAD, GET and PUT. Otherwise uploads fail.
4. Allow the new origin in the Function App CORS list if the browser calls the API directly.

**C. Host `app/` somewhere else (for example a storage static website or an App Service).** This also needs the redirect URI and storage CORS steps above. The Static Web App login rules in `staticwebapp.config.json` only apply on SWA; on other hosts, token checks depend on MSAL in `index.html` and the Function App's Easy Auth.

Use a preview environment only for testing. Delete it once you are done. Each preview needs its own redirect URI and storage CORS entry.

## 7. Deploying the Function App (back end)

```powershell
cd "C:\Users\ali.ahmadi\OneDrive - fma.govt.nz\Documents\GitHub\pdfocr\api"
python -m py_compile function_app.py
findstr /i "<a href" function_app.py
func azure functionapp publish fn-pdfocr-api --python --build remote
```

The compile check returns no output when it passes. The `findstr` check must return nothing, because the API returns plain URLs, not HTML. Test:

- `https://fn-pdfocr-api.azurewebsites.net/api/hello` returns `Hello works`.
- `/api/upload?filename=test.pdf` with a valid token returns an `https://` SAS URL.
- A request without a token returns 401.

Front-end and back-end deployments are independent. When an API change affects `index.html`, deploy both and test the whole flow.

## 8. Security

### Current state (2026-11-21)

- Storage: anonymous blob access off. Shared key access still on. Both account keys were regenerated on 2026-11-20; the Function App and SWA use key2.
- Function App: HTTPS only. Easy Auth enforced (Return401). CORS allows only the SWA origin.
- Static Web App: sign-in required for all routes except `/redirect.html`.
- Entra: assignment required on both apps. Client secret for `FMA PDF OCR Tool` rotated on 2026-11-20 and valid for one year.
- Document Intelligence: both keys regenerated. The Function App and SWA use key2.
- Power Apps origin removed from storage CORS. The storage account is believed to be used only by this app; the owner should confirm this.
- SWA `preview` environment deleted.

### Remaining gaps, in priority order

1. **Shared keys in app settings (partly done).** The Function App now uses its managed identity for blob access and user-delegation SAS links. `STORAGE_ACCOUNT_KEY` has been removed. Still open: the Consumption content share (`WEBSITE_CONTENTAZUREFILECONNECTIONSTRING`) and `AzureWebJobsStorage` still use account keys, so shared key access on the storage account cannot be turned off until the plan changes. Document Intelligence still uses `DOCINTEL_KEY`.
2. **Network restriction.** The storage account and Document Intelligence still accept public traffic. Restrict to the Function App's outbound addresses or private endpoints where possible.
3. **Key Vault.** Move `AZURE_CLIENT_SECRET`, `DOCINTEL_KEY` and the storage key into Key Vault references.
4. **Input validation in `/api/upload`.** It signs an upload URL for any filename and does not limit size or type. Add an extension allow-list and a size limit.
5. **Access review.** Review `App_PdfOCR_Users` and the enterprise app assignments on a schedule.
6. **Two sign-in layers.** The SWA login and the MSAL sign-in both ask the user to sign in. Decide whether to keep both.

Old backup folders with earlier secrets were deleted on 2026-11-20. Do not create copies of `app/` or the settings in OneDrive or elsewhere.

## 9. Operations runbook

### Rotate the storage account key

The app itself no longer uses a storage key. The key is still needed for the Function App's `AzureWebJobsStorage` and content share, and the SWA's `AzureWebJobsStorage`.

1. Regenerate **key2** (`az storage account keys renew -n pdfocrvzeotjuko574ust -g rg-pdf-ocr --key secondary`).
2. Set the new key2 in the Function App (`AzureWebJobsStorage`) and on the SWA default environment (`AzureWebJobsStorage`).
3. Test `/api/upload` and a small conversion.
4. Regenerate **key1** and leave it unused until the next rotation.

Use `--query` or `-o none` so the key is not printed. Clear the output before closing the terminal.

### Rotate Document Intelligence keys

Same pattern: regenerate key2, set `DOCINTEL_KEY` on the Function App and the SWA, test, then regenerate key1.

### Rotate the SWA login client secret

Entra → App registrations → `FMA PDF OCR Tool` → Certificates & secrets. Create a new secret, set `AZURE_CLIENT_SECRET` on the SWA default environment, test sign-in, then delete the old secret. Record the expiry date. The current secret expires one year after 2026-11-20.

### Add or remove a user

Add or remove them in `App_PdfOCR_Users`. This takes effect for new sign-ins. No deployment is needed. If a user is not in a group, they should be blocked by "Assignment required"; test this when making changes.

### Check the purge rule

Storage → Lifecycle management, or:

```powershell
az storage account management-policy show --account-name pdfocrvzeotjuko574ust -g rg-pdf-ocr
```

Expect one rule that covers `uploads/` and `outputs/`. Do not change it without telling the users, since it deletes results after about 2 to 3 days.

### Check that the app is up

1. `https://fn-pdfocr-api.azurewebsites.net/api/hello` returns `Hello works`.
2. The site redirects to sign-in.
3. Upload a small PDF, convert it, and download the result and the ZIP.

### Find errors

Application Insights linked to `fn-pdfocr-api` (Failures and Logs). For the front end, use the browser developer tools Network tab.

## 10. Troubleshooting

| Symptom | Likely cause | Check |
|---|---|---|
| "SAS failed" | Function unreachable, unauthenticated, or missing settings | `/api/hello`; Function settings; sign-in |
| "Failed to fetch" on upload (sign-in works) | Storage CORS does not include the site origin | Storage → Resource sharing (CORS) |
| HTTP 401 from the API | Token missing or expired, or the user is not assigned | Sign out and back in; check assignment |
| Sign-in loops or lands on site root | Redirect URI missing on `FMA PDF OCR Tool` | Authentication → redirect URIs |
| Sign-in popup blocked | Browser setting | Allow popups for the site |
| `PublicAccessNotPermitted` (409) on a list request | Expected; anonymous access is off | Use a SAS URL |
| Output named `filename_ocr.pdf` | Old code deployed | Redeploy the Function App |
| Download link shows raw HTML or a long SAS URL | Backend returned HTML | Check `/api/upload` in the Network tab |
| Compile error `IndentationError` | Copied code with wrong spacing | `python -m py_compile function_app.py` |
| Results missing after a few days | Lifecycle rule working as designed | Expected |

## 11. Costs

Main cost drivers:

- **Document Intelligence (S0).** Billed per page. This is usually the largest variable cost. Scanned folders with many pages drive it up.
- **Static Web App (Standard).** A fixed monthly fee. The current setup uses the Standard SKU; check whether the Free tier can still be used before changing it.
- **Storage.** Small, because the lifecycle rule deletes files after about 2 to 3 days. Keep the rule to control this.
- **Function App (Consumption).** Charged per execution and duration. Light use keeps it low.
- **Application Insights.** Charged by ingested data. Reduce logging if it grows.

To reduce costs: shorten the retention window (with user agreement), delete unused resources, and check the Cost analysis for `rg-pdf-ocr` each month.

## 12. Backup and recovery

- **Code.** The GitHub repository `aliahmadi76/pdfocr` (branch `main`) is the source of truth. Use a branch before risky changes.
- **Output files.** Not backed up. The lifecycle rule deletes them after about 2 to 3 days. If a result must be kept, the user must download it in time. Do not treat the tool as storage.
- **Settings.** Export the Function App and SWA settings to a private file outside the repo before changing them. Do not commit the export.
- **Azure resources.** `infra/main.bicep` can recreate most resources, but the live environment has drifted (for example the Function App and Entra apps are not in it). Use `az deployment group what-if` and compare before any redeploy.
- **Entra apps.** Recreating `pdfocr-api` and `FMA PDF OCR Tool` requires the redirect URIs, the `user_impersonation` scope, app role or group assignments, and the client secret. Write these down whenever they change.
- **Recovery order:** resource group → storage account and containers → Document Intelligence → Function App and plan → Entra apps → Static Web App → settings → GitHub secret `AZURE_STATIC_WEB_APPS_API_TOKEN` → deploy both code halves → test.

## 13. Known issues and open questions

- The SWA is in East Asia, while the other resources are in Australia East. Check whether the split is intended; it may add latency.
- Sign-in, upload, conversion and download were confirmed working by the owner on 2026-11-21, after the managed identity change.
- The reason the earlier popup sign-in hung was not confirmed.
- `api/function_app.py` is committed with the indentation fix. Its earlier uncommitted edits are no longer open.
- Remote branches `secure-auth`, `fix-popup-sign-in` and `pre-auth-backup` still exist. Delete them only after the owner agrees.

## 14. Further reading

- [Overview and security status](APP_OVERVIEW.md)
- [Deployment guide](DEPLOYMENT.md)
- [Function App deployment](FUNCTION_APP_DEPLOYMENT.md)
- [Architecture notes](ARCHITECTURE.md)
- [Troubleshooting](TROUBLESHOOTING.md)
- [Support checklist](SUPPORT_CHECKLIST.md)
