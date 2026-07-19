# Function App Deployment Guide

## Location

```powershell
cd "C:\Users\ali.ahmadi\OneDrive - fma.govt.nz\Documents\GitHub\pdfocr\api"
```

Expected files:

```text
function_app.py
host.json
requirements.txt
```

## Pre-deployment checks

```powershell
python -m py_compile function_app.py
findstr /i "<a href" function_app.py
```

Expected:

- Python compile returns no output.
- `findstr` returns no output.

## Identify Function App name

```powershell
az login
az functionapp list --query "[].name" -o table
```

## Publish

```powershell
func azure functionapp publish <FUNCTION_APP_NAME> --python --build remote
```

## Verify

```text
https://<FUNCTION_APP_NAME>.azurewebsites.net/api/hello
```

Expected response:

```text
Hello works
```
