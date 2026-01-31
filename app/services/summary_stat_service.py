from app.config import get_settings
from typing import List
import io
import zipfile
import os
from app.models.schemas import ExtendedStudyExtraction
from app.services.oci_service import OCIService
from app.logging_config import get_logger

settings = get_settings()
logger = get_logger(__name__)


class SummaryStatService:
    def __init__(self):
        self.oci_service = OCIService()

    def get_study_summary_stats(self, study_extractions: List[ExtendedStudyExtraction]):
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            for study_extraction in study_extractions:
                file_name = f"{study_extraction.study_id}_with_lbfs.tsv.gz"

                try:
                    object_name = study_extraction.file_with_lbfs
                    if not object_name:
                        logger.warning(f"No file path for study extraction {study_extraction.id}")
                        continue

                    response = self.oci_service.get_file(object_name)
                    zip_file.writestr(file_name, response)
                except Exception as e:
                    logger.error(f"Failed to fetch summary stats for study {study_extraction.study_id} from OCI: {e}")
                    continue

        zip_buffer.seek(0)
        return zip_buffer
