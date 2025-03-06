#! /bin/bash
cd "$(dirname "$0")"

# triggered every hour by a cron job
echo start script - $(date)

echo spinning up mongo container
/usr/local/bin/docker compose up -d 

echo running ingestion script
/usr/bin/python3 ingest.py 2>&1

echo running parse script
/usr/bin/python3 parse.py 2>&1

/usr/local/bin/docker compose down

echo end script - $(date)