#! /bin/bash

# triggered every hour by a cron job

if docker volume inspect notam-data 2>&1 | grep -q 'no such volume' ; then
  echo notam-data volume not present, creating
  docker volume create notam-data &> /dev/null
  echo notam-data volume created
fi

if docker volume inspect notam-config 2>&1 | grep -q 'no such volume' ; then
  echo notam-config volume not present, creating
  docker volume create notam-config &> /dev/null
  echo notam-config volume created
fi

echo spinning up mongo container
docker compose up -d

echo running ingestion script
python3 ingest.py

echo running parse script
python3 parse.py

docker compose down