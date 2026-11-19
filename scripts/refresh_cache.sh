#!/bin/bash
set -e

# curl -X POST "http://127.0.0.1:8000/v1/internal/clear-cache/studies"
curl -X POST "http://127.0.0.1:8000/v1/internal/clear-cache/all"
echo "All redis caches cleared"

curl "http://127.0.0.1:8000/v1/info/gpmap_metadata" > /dev/null
curl "http://127.0.0.1:8000/v1/search/options" > /dev/null
curl "http://127.0.0.1:8000/v1/traits" > /dev/null
curl "http://127.0.0.1:8000/v1/genes" > /dev/null

# We don't need to set associations cache for all studies anymore, as we now use the new associations database
# Only the most expensive traits (>= 1M associations-full rows, ~6GB of columnar cache in total), largest first;
# smaller traits are fast enough to compute on demand. Sizes measured against the new associations_full.db.
trait_ids=(
    1993 1984 168 2586 4532 3516 935 2587 3143 3265 937 1640 1986 4472 3499 926 3395 1982 1983 3084 4303 1981 3709
    1988 928 924 932 1980 938 1647 1641 2588 923 4765 2582 2589 1630 4353 2625 920 930 1284 931 933 2612 2590 4776
    4778 3342 939 2606 1652 1992 2584 1631 1629 918 927 1996 4241 4400 2598 1481
)

for trait_id in "${trait_ids[@]}"; do
    echo "Setting associations cache for: $trait_id"
    curl "http://127.0.0.1:8000/v1/traits/$trait_id/associations-full?format=columnar" > /dev/null
done
