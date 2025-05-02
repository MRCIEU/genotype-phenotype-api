#!/bin/bash
set -e

echo "Deleting old unused data and databases"

rm -rf /oradiskvdb1/data/ld_blocks_backup
rm -rf /oradiskvdb1/data/ld_blocks_new
rm /oradiskvdb1/db/ld_backup.db
rm /oradiskvdb1/db/ld_new.db
rm /oradiskvdb1/db/associations_backup.db
rm /oradiskvdb1/db/associations_new.db
rm /oradiskvdb1/db/studies_backup.db
rm /oradiskvdb1/db/studies_new.db

echo "Done"
