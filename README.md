# Setting up

When not using the docker-compose setup of the [main-repository](https://github.com/vktrrdk/nextflowAnalysis), using a virtual environment is suitable.

There are several default values set in the `.env`-file and can be changed if wished. This includes:
- `POSTGRES_HOST`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_PORT`


To locally start the application, source the `setEnv.sh`.
Then use the `compose.yml` to start the local database.

After starting the database, change the directory with `cd fastapi` and install the needed packages with `pip install -r requirements.txt`.

Then start the application with `uvicorn main:app --reload --port 8000 --host localhost`, to make the API available at port `8000`.>

If this is the first execution, go into the alembic-directory (preferably with another terminal instance) with `cd alembic` and run the database migrations with `alembic upgrade head`.

