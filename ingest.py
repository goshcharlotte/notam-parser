import os
import pymongo
import datetime
import pprint
import requests

from dotenv import load_dotenv
load_dotenv()

mongo_username = os.getenv('MONGO_USERNAME')
mongo_password = os.getenv('MONGO_PASSWORD')

# start connection to mongodb
mongo_client = pymongo.MongoClient(f'mongodb://localhost:27017/',
                                   username=mongo_username,
                                   password=mongo_password)
notam_db = mongo_client.notam

# pull latest PIB from nats: https://pibs.nats.co.uk/operational/pibs/PIB.xml (updated every hour)
response = requests.get('https://pibs.nats.co.uk/operational/pibs/PIB.xml')

# dump contents of xml into mongodb and record local timestamp and issue timestamp of dump
latest_dump = {
    'content': response.text,
    'retrieved': datetime.datetime.now(tz=datetime.timezone.utc)
}

dump_result = notam_db.datadumps.insert_one(latest_dump)

print(mongo_client.list_database_names())
print(notam_db.list_collection_names())

# for testing: retrieve latest dump from collection
pprint.pprint(notam_db.datadumps.find_one(sort=[('retrieved', pymongo.DESCENDING)]))
