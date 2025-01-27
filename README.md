# Genotype-phenotype map API

## Background

Using [fastapi](http://fastapi.tiangolo.com) framework with a postgres database to store genotype-phenotype map data.

## Overview

![alt text](image.png)

## Database design

![Database design](db/genotype-phenotype-map_1.png)

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
   DATABASE_URL=postgresql://user:password@db:5432/mydatabase
   POSTGRES_USER=user
   POSTGRES_PASSWORD=password
   POSTGRES_DB=mydatabase
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
   DATABASE_URL=postgresql://user:password@db:5432/mydatabase
   POSTGRES_USER=user
   POSTGRES_PASSWORD=password
   POSTGRES_DB=mydatabase
   ANALYTICS_KEY=7a2b8f79-c837-45fa-ac48-0967ba8acf1b
   ```

3. Build and run the Docker containers:
   ```
   docker-compose up --build
   ```

4. The API will be available at `http://localhost:8000`

## Populate the database

```
python -m app.db.populate_db app/db/items.csv 
```

## Running Tests

To run the unit tests, make sure you're in the development container, then execute:

```
pytest app/test_main.py
```

If you're not in the development container, you can run the tests using Docker Compose:

```
docker-compose run web pytest app/test_main.py
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


## Development notes





