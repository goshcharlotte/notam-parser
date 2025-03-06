# notam-parser

A project to ingest, parse, and maintain NOTAM data for UK airspace. 

## Installation
Make sure docker, python3, and pip3 are installed and available on your PATH, then run the following in the project root to install python libraries, set up docker volumes, and schedule a cron job to run the ingest/parse scripts and pull data hourly:
```sh 
./setup.sh
```

If you face issues with this, make sure that `cron` is using the same version of python, pip, and docker by running `which python3` etc in both a normal bash shell and inside a test cron job and comparing results.


### Variables
Add a local `.env` file that contains vars for Mongo configuration:
```
MONGO_USERNAME=notamadmin
MONGO_PASSWORD=admin
MONGO_INITDB_DATABASE=notam
DB_COLLECTION='pib'
DB_HOST='localhost'
```


## Docker Compose
The `docker-compose.yml` file spins up two containers:
1. A mongodb database to store NOTAM data
1. A mongo-express container that allows GUI access to the database from the web via [`http://localhost:8081`]()

These containers rely on two external volumes existing already:
- `notam-data` - persistent storage for NOTAMs in Mongo
- `notam-config` - config storage for Mongo container

Running `setup.sh` for the first time will create these volumes and persist NOTAM data even when the containers are not running.

Launch the containers for local development by running
```sh
docker compose up -d
```


## Scheduler Script
To avoid constantly running a MongoDB container while NOTAM data is being collected and parsed, the `notam-scheduler.sh` script:
1. Spins up the database docker containers via docker compose
1. Runs ingest.py
1. Runs parse.py
1. Stops the docker containers

This is intended for use in the hourly scheduled cron job but can also be useful for local dev. 


## TODO
- retrieve the `Issued` field from within the xml data dump and compare it to the previous latest data dump - don't save the newer one if it was issued at the same time