# Spreadsheet Data Quality Audit — Fictional Sample

> Publication status: prepared locally for a future public GitHub repository. No remote repository or GitHub release has been created, and the preparation process performed no external write.

> [!IMPORTANT]
> This repository is a fixed fictional evidence sample, not an open-source spreadsheet audit tool.
> `verify_release.py` only checks package integrity and publication state. It cannot scan a new workbook, and the paid audit engine and launcher are not included.

Inspect a complete fictional input and its redacted audit outputs before deciding whether the paid offline toolkit fits your workflow.

This public sample contains 26 fictional order rows, 6 columns, and 16 finding records across 10 distinct issue codes. The v1.0 JSON and Markdown outputs keep the legacy field label `issue_categories` for schema compatibility; its value counts finding records grouped by severity, code, and column, not 16 distinct codes. The generated report keeps filenames, headers, counts, row references, and hashes as review metadata, but does not copy original data-row cell values into the output.

## What is included

- sample/fictional-orders-with-issues.xlsx — a deliberately imperfect fictional workbook.
- sample-output/audit-report.xlsx — the generated issue register and review sheets.
- sample-output/audit-summary.md — a human-readable result summary.
- sample-output/audit-manifest.json — scope, counts, hashes, and output evidence.
- assets/ — the product cover and a fictional report preview.
- release/Spreadsheet-Data-Quality-Audit-Sample-v1.0.0.zip — the same sample files in one integrity-checked archive.

No paid engine, PowerShell launcher, editable source code, commercial license, customer file, credential, or private operating document is included.

## A five-minute inspection

1. Open the fictional input and confirm that it contains only demonstration records.
2. Open the Excel report and review the finding codes, severities, columns, counts, and row references.
3. Compare those totals with audit-summary.md.
4. Confirm the source and output hashes in audit-manifest.json.
5. Read the boundary: this is rule-based preflight evidence, not an accounting audit, repair service, compliance review, or guarantee that every error is detected.

## Paid offline toolkit

The paid toolkit runs locally on Windows against one authorized .xlsx or comma-delimited .csv at a time. It supports up to 10,000 data rows and 30 columns and generates an Excel issue register, Markdown summary, and SHA-256 manifest.

- [Review the exact Personal, Consultant, and Agency scope](https://payment-flow-studio-tw.masstech.chatgpt.site/en/tools/spreadsheet-data-quality-audit-toolkit?source=github_e21_sample)
- [Open the tested Gumroad product](https://toolcraftstudio.gumroad.com/l/spreadsheet-data-quality-audit-toolkit)
- [Read the versioned license terms](https://payment-flow-studio-tw.masstech.chatgpt.site/en/terms/spreadsheet-data-quality-audit-toolkit-v1)

Personal is US$39 for one named person and one internal organization. Consultant is US$129 for one named consultant and up to 10 client organizations. Agency is US$299 for up to five named users and 50 client organizations. Review the versioned terms before purchase.

## Verify this public release

Python 3 is sufficient; the verifier uses only the standard library.

    python -B .\verify_release.py --state published

For the same integrity and publication-state checks without live HTTP requests:

    python -B .\verify_release.py --state published --offline

Before the repository is published, the owner can run:

    python -B .\verify_release.py --state prepared

## Privacy and safety

The included data is fictional. Do not replace it with a real customer workbook in this public repository. The sample contains no macros or executable code. Open downloaded spreadsheet files using your normal organizational security controls.

This repository does not claim sales, downloads, revenue, time saved, error-free operation, or guaranteed business results.
