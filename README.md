# notam-parser

A project to ingest, parse, and maintain NOTAM data for UK airspace. 

## Installation
Make sure docker, python3, and pip are installed and available on your PATH, then run the following in the project root to install python libraries, set up docker volumes, and retrieve the most recent NOTAM data dump:

```sh
pip install -r requirements.txt
./scheduler.sh
```

### Variables
Add a local `.env` file that contains vars for Mongo setup:
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
Running `scheduler.sh` for the first time will create these volumes and persist NOTAM data even when the containers are not running.


## Scheduler Script
To avoid constantly running a MongoDB container while NOTAM data is being collected and parsed, the `scheduler.sh` script:
1. Checks for and creates all required docker volumes
1. Spins up the database docker containers via docker compose
1. Runs ingest.py
1. Runs parse.py
1. Stops the docker containers

This is intended for use in an hourly scheduled cron job but can also be useful for local dev. 


## TODO
- retrieve the `Issued` field from within the xml data dump and compare it to the previous latest data dump - don't save the newer one if it was issued at the same time
- parse xml data dump into db in `parse.py' script