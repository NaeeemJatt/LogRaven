# LogRaven — Report Uploader
#
# PURPOSE:
#   Moves the generated PDF from temp storage to permanent report storage.
#   Uses the StorageBackend abstraction — same code works local and S3.
#
# MAIN FUNCTION:
#   upload_report(temp_path, investigation_id) -> str (storage_key)
#
# STORAGE KEY FORMAT:
#   reports/{investigation_id}/lograven-report-{uuid}.pdf
#
# After upload: temp file is deleted.
# The storage_key is saved to the Report.pdf_storage_key column.
#
# TODO Month 4 Week 1: Implement this file.
