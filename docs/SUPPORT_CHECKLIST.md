# PDF OCR Tool Support Checklist

Before deployment:

- [ ] Correct repo/folder is open.
- [ ] All files saved in VS Code.
- [ ] `git status` reviewed.
- [ ] `python -m py_compile function_app.py` returns no output.
- [ ] `findstr /i "<a href" function_app.py` returns no output.
- [ ] `const BASE` in `index.html` is a plain URL.
- [ ] Front-end changes committed and pushed.
- [ ] Function App published from the API folder.

After deployment:

- [ ] `/api/hello` returns `Hello works`.
- [ ] `/api/upload?filename=test.pdf` returns a raw SAS URL.
- [ ] Upload test PDF through UI.
- [ ] Confirm output appears under expected Blob path.
- [ ] Confirm individual download link works.
- [ ] Confirm ZIP download works.
- [ ] Confirm OCR log files are included in ZIP.
