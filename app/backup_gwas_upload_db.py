"""
Upload a timestamped snapshot of gwas_upload.db to the API OCI bucket.

Invoked from the host via docker exec, e.g. scripts/backup_gwas_upload_db.sh
"""

import sys

from app.config import get_settings
from app.logging_config import get_logger
from app.services.oci_service import OCIService

logger = get_logger(__name__)


def main() -> int:
    settings = get_settings()
    db_path = settings.GWAS_UPLOAD_DB_PATH

    try:
        object_name = OCIService().backup_gwas_upload_db(db_path)
    except FileNotFoundError as exc:
        logger.warning(f"{exc}. Skipping OCI backup.")
        return 0
    except ValueError as exc:
        logger.error(f"OCI backup failed: {exc}")
        return 1
    except Exception as exc:
        logger.error(f"Failed to back up GWAS upload database: {exc}")
        return 1

    print(f"Backed up {db_path} to {object_name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
