#!/bin/bash
set -e

sudo docker compose pull
sudo docker compose down

echo "Swapping to new databases"
mv /oradiskvdb1/db/studies.db /oradiskvdb1/db/studies_backup.db
mv /oradiskvdb1/db/studies_new.db /oradiskvdb1/db/studies.db

mv /oradiskvdb1/db/coloc_pairs.db /oradiskvdb1/db/coloc_pairs_backup.db
mv /oradiskvdb1/db/coloc_pairs_new.db /oradiskvdb1/db/coloc_pairs.db

mv /oradiskvdb1/db/associations.db /oradiskvdb1/db/associations_backup.db
mv /oradiskvdb1/db/associations_new.db /oradiskvdb1/db/associations.db

mv /oradiskvdb1/db/ld.db /oradiskvdb1/db/ld_backup.db
mv /oradiskvdb1/db/ld_new.db /oradiskvdb1/db/ld.db

echo "Swapping to new study information for gwas upload"
mv /oradiskvdb1/data/ld_blocks /oradiskvdb1/data/ld_blocks_backup
mv /oradiskvdb1/data/ld_blocks_new /oradiskvdb1/data/ld_blocks
mkdir -p /oradiskvdb1/data/ld_blocks_new

echo "Swapping to new svgs"
mv /oradiskvdb1/static/svgs /oradiskvdb1/static/svgs_backup
mv /oradiskvdb1/static/svgs_new /oradiskvdb1/static/svgs
mkdir -p /oradiskvdb1/static/svgs_new

sudo docker compose up -d

echo "Done"
