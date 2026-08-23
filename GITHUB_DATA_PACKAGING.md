# GITHUB DATA PACKAGING

For the final UniHack GitHub submission, the offline knowledge corpus must be packaged appropriately.

## Included Directory
The following directory MUST be included in the repository structure:
`data_storage/permanent_knowledge/`

## Large Files
The total size of the current dataset is ~16 MB. Since no individual file exceeds 100 MB, Git Large File Storage (LFS) is **NOT** strictly required. The entire payload can be natively committed to the GitHub repository.

## State Preservation
Ensure that the following generated files are committed so that the backend acknowledges the initialized state without needing to re-download the payload:
- `permanent_knowledge_manifest.json`
- `retrieval_verification.json`
- `coverage_matrix.json`
- `final_storage_audit.json`
- `industry_coverage.json`
- `knowledge_gap_report.json`
- `rejected_datasets.json`

## Execution
*Note: This is a read-only audit. No `git commit` or `git push` commands have been executed.*
