# PDF OCR Tool Architecture

```text
User browser
  -> Azure Static Web App
  -> Azure Function App
  -> Azure AI Document Intelligence
  -> Azure Blob Storage
```

## Blob containers

```text
uploads   - source PDF uploads
outputs   - OCR output PDFs
```

## Batch folders

The browser generates a `job_id`. The Function App uses this in the output blob path:

```python
blob_name = f"{job_id}/{filename}"
```

This creates a virtual folder structure:

```text
outputs/
  <job_id>/
    document1.pdf
    document2.pdf
```

Azure Blob Storage presents folders virtually based on `/` characters in the blob name.
