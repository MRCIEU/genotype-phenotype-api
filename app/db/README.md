The database is a duckdb database and is generated from the pipeline files using R

```
sudo docker build -t gpmap_duckdb -f Dockerfile.duckdb .
docker run -v $(pwd)/data:/project/data gpmap_duckdb Rscript /project/process.r /project/data /project/data/gpmap.db
```
