#!/bin/bash
set -e

sudo docker compose pull
sudo docker compose down

echo "Swapping to new databases"
cp /oradiskvdb1/db/studies.db /oradiskvdb1/db/studies_backup.db
cp /oradiskvdb1/db/studies_new.db /oradiskvdb1/db/studies.db

cp /oradiskvdb1/db/associations.db /oradiskvdb1/db/associations_backup.db
cp /oradiskvdb1/db/associations_new.db /oradiskvdb1/db/associations.db

cp /oradiskvdb1/db/ld.db /oradiskvdb1/db/ld_backup.db
cp /oradiskvdb1/db/ld_new.db /oradiskvdb1/db/ld.db

echo "Swapping to new study information for gwas upload"
mv /oradiskvdb1/data/ld_blocks /oradiskvdb1/data/ld_blocks_backup
mv /oradiskvdb1/data/ld_blocks_new /oradiskvdb1/data/ld_blocks

sudo docker compose up -d

echo "Done"
