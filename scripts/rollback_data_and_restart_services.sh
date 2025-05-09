#!/bin/bash
set -e

sudo docker compose pull
sudo docker compose down

echo "Swapping back to old databases"
mv /oradiskvdb1/db/studies.db /oradiskvdb1/db/studies_new.db
mv /oradiskvdb1/db/studies_backup.db /oradiskvdb1/db/studies.db

mv /oradiskvdb1/db/associations.db /oradiskvdb1/db/associations_new.db
mv /oradiskvdb1/db/associations_backup.db /oradiskvdb1/db/associations.db

mv /oradiskvdb1/db/ld.db /oradiskvdb1/db/ld_new.db
mv /oradiskvdb1/db/ld_backup.db /oradiskvdb1/db/ld.db

echo "Swapping back to old ld blocks"
mv /oradiskvdb1/data/ld_blocks /oradiskvdb1/data/ld_blocks_new
mv /oradiskvdb1/data/ld_blocks_backup /oradiskvdb1/data/ld_blocks
mkdir -p /oradiskvdb1/data/ld_blocks_new

sudo docker compose up -d

echo "Done"
