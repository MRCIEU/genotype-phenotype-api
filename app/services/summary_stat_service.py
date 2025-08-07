from app.config import get_settings
from typing import List
import io
import zipfile
import os
from app.models.schemas import ExtendedStudyExtraction

settings = get_settings()


class SummaryStatService:
    def __init__(self):
        self.summary_stats_dir = settings.SUMMARY_STATS_DIR

    def get_study_summary_stats(self, study_extractions: List[ExtendedStudyExtraction]):
        if settings.DEBUG:
            all_files = os.listdir(self.summary_stats_dir)
            file_names = [os.path.join(self.summary_stats_dir, f) for f in all_files]

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            for study_extraction in study_extractions:
                file_name = str(study_extraction.study_id) + "_with_lbfs.tsv.gz"
                if settings.DEBUG:
                    file_path = file_names[study_extraction.id % len(file_names)]
                else:
                    file_path = study_extraction.file_with_lbfs

                zip_file.write(file_path, arcname=file_name)
        zip_buffer.seek(0)

        return zip_buffer
