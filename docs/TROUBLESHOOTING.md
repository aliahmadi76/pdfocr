# PDF OCR Tool Troubleshooting

## SAS failed

This usually means `/api/upload` failed or returned something other than a successful response.

Check:

```text
https://<FUNCTION_APP_NAME>.azurewebsites.net/api/hello
https://<FUNCTION_APP_NAME>.azurewebsites.net/api/upload?filename=test.pdf
```

`/api/upload` should return a raw URL beginning with `https://`.

## Download link shows raw SAS URL

The backend should return raw URLs only. The front-end creates the anchor tag.

Correct JavaScript pattern:

```javascript
setStatus(
  item,
  "done",
  '<a href="' + downloadUrl + '" target="_blank">📥 Download</a>'
);
```

## Output still appears as filename_ocr.pdf

The deployed Function App is probably still running older code.

Search local code:

```powershell
findstr /s /i "_ocr.pdf" *.py
```

Then redeploy the correct Function App.

## Python syntax errors

Run:

```powershell
python -m py_compile function_app.py
```

Fix any line numbers reported before publishing.
