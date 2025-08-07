#!/bin/bash
set -e

sudo docker compose pull
sudo docker compose down

echo "Swapping to new databases"
if [ -f /oradiskvdb1/db/studies_new.db ]; then
    mv /oradiskvdb1/db/studies.db /oradiskvdb1/db/studies_backup.db
    mv /oradiskvdb1/db/studies_new.db /oradiskvdb1/db/studies.db
fi

if [ -f /oradiskvdb1/db/coloc_pairs_new.db ]; then
    mv /oradiskvdb1/db/coloc_pairs.db /oradiskvdb1/db/coloc_pairs_backup.db
    mv /oradiskvdb1/db/coloc_pairs_new.db /oradiskvdb1/db/coloc_pairs.db
fi

if [ -f /oradiskvdb1/db/associations_new.db ]; then
    mv /oradiskvdb1/db/associations.db /oradiskvdb1/db/associations_backup.db
    mv /oradiskvdb1/db/associations_new.db /oradiskvdb1/db/associations.db
fi

if [ -f /oradiskvdb1/db/ld_new.db ]; then
    mv /oradiskvdb1/db/ld.db /oradiskvdb1/db/ld_backup.db
    mv /oradiskvdb1/db/ld_new.db /oradiskvdb1/db/ld.db
fi

rm -rf /oradiskvdb1/data/ld_blocks_backup
mv /oradiskvdb1/data/ld_blocks /oradiskvdb1/data/ld_blocks_backup
mv /oradiskvdb1/data/ld_blocks_new /oradiskvdb1/data/ld_blocks
mkdir -p /oradiskvdb1/data/ld_blocks_new

echo "Swapping to new svgs"
rm -rf /oradiskvdb1/static/svgs_backup
mv /oradiskvdb1/static/svgs /oradiskvdb1/static/svgs_backup
mv /oradiskvdb1/static/svgs_new /oradiskvdb1/static/svgs
mkdir -p /oradiskvdb1/static/svgs_new

sudo docker compose up -d --remove-orphans

echo "Done"
