from app.services.oci_service import GWAS_UPLOAD_DB_BACKUP_PREFIX, OCIService


def test_backup_gwas_upload_db_uploads_timestamped_snapshot(tmp_path, mocker):
    db_path = tmp_path / "gwas_upload.db"
    db_path.write_bytes(b"duckdb-data")

    upload_file = mocker.patch.object(OCIService, "upload_file", return_value="uploaded")
    mocker.patch.object(OCIService, "__init__", lambda self: None)

    service = OCIService()
    service.bucket_name = "gp_map_storage"
    object_name = service.backup_gwas_upload_db(str(db_path))

    assert object_name == f"{GWAS_UPLOAD_DB_BACKUP_PREFIX}/gwas_upload.db"
    upload_file.assert_called_once()
    uploaded_path, uploaded_object_name = upload_file.call_args.args[:2]
    assert uploaded_object_name == object_name
    assert uploaded_path != str(db_path)
