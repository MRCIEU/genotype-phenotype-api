#!/bin/bash
set -e

echo "Deleting old unused data and databases"

rm /home/opc/gpmap_data/db/ld_backup.db
rm /home/opc/gpmap_data/db/ld_new.db
rm /home/opc/gpmap_data/db/associations_backup.db
rm /home/opc/gpmap_data/db/associations_new.db
rm /home/opc/gpmap_data/db/associations_full_backup.db
rm /home/opc/gpmap_data/db/associations_full_new.db
rm /home/opc/gpmap_data/db/studies_backup.db
rm /home/opc/gpmap_data/db/studies_new.db
rm /home/opc/gpmap_data/db/coloc_pairs_backup.db
rm /home/opc/gpmap_data/db/coloc_pairs_new.db

echo "Done"
