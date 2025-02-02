# Genotype-phenotype map API

## Background

Using [fastapi](http://fastapi.tiangolo.com) framework with a postgres database to store genotype-phenotype map data.

## Overview

![alt text](strategy.png)

## Endpoints

- List traits
- List regions
- LD between variants

## Prerequisites

- Docker and Docker Compose
- Visual Studio Code with Remote - Containers extension for development

## Setup and Running

### Development

1. Clone the repository:
   ```
   git clone https://github.com/mrcieu/genotype-phenotype-api.git
   cd genotype-phenotype-api
   ```

2. Create a `.env` file

   ```
   ANALYTICS_KEY=7a2b8f79-c837-45fa-ac48-0967ba8acf1b
   DB_PROCESSED_PATH="data/processed.db"
   DB_ASSOCS_PATH="data/assocs.db"
   LOCAL_DB_DIR="/local-scratch/projects/genotype-phenotype-map/results/2025_01_28-13_04"
   ```

3. Open the project in VSCode:

   ```
   code .
   ```

4. When prompted, click "Reopen in Container". This will start the development environment.

5. Once the container is built and running, you can start the FastAPI server by running:

   ```
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

6. The API will be available at `http://localhost:8000`, and the code will hot-reload on changes.

Or if not using VSCode

1. Clone the repository:
   ```
   git clone https://github.com/mrcieu/genotype-phenotype-api.git
   cd genotype-phenotype-api
   ```

2. Create a `.env` file

   ```
   ANALYTICS_KEY=<key from https://my-api-analytics.vercel.app>
   ```

3. Build and run the Docker containers:

   ```
   docker-compose up --build
   ```

4. The API will be available at `http://localhost:8000`

## Populate the database

The database is a duckdb database and is generated from the pipeline files using R

```
cd app/db
docker build --platform linux/amd64 -t gpmap_duckdb -f Dockerfile.duckdb .
docker run -v $(pwd)/data:/project/data gpmap_duckdb Rscript /project/process.r /project/data /project/data/gpmap.db
cd -
```

## CI/CD

The project includes a GitHub Actions workflow for Continuous Integration and Deployment. On each push to the main branch, it will:

1. Run the unit tests
2. Build a Docker image
3. Push the image to Docker Hub (using secrets DOCKER_USERNAME and DOCKER_PASSWORD configured in github repo)

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the GPL3 License.
