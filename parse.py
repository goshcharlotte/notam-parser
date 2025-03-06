from typing import Any, OrderedDict
from pymongo import MongoClient # type: ignore

import asyncio
import logging
import os
import requests
import sys
import xmltodict # type: ignore
from dotenv import load_dotenv

import notifications as notification_function  # noqa: E402

load_dotenv()


logging.basicConfig(format="%(asctime)s %(levelname)s:%(message)s")
logging.getLogger().setLevel(logging.INFO)

async def run(args=None):
    """Function main method. """
    mongo_db_username, mongo_db_password, mongo_db_name, mongo_db_port, mongo_db_host, mongo_db_collection = get_mongo_credentials()

    # connect to the database
    uri = f"mongodb://{mongo_db_username}:{mongo_db_password}@{mongo_db_host}:{mongo_db_port}/{mongo_db_name}?authSource=admin"
    client = MongoClient(uri)
    db = client[f"{mongo_db_name}"]

    # Collection
    json_collection = db[f"{mongo_db_collection}"]
    xml_id_field = '@PIBId'
   
    data = get_xml_data()

    if data['Pib'][xml_id_field] is not None:
        result = json_collection.replace_one({xml_id_field : data['Pib'][xml_id_field] }, data['Pib'],True)
        id_value = data['Pib'][xml_id_field]
        print(f"{xml_id_field} : {id_value} inserted... {result}")
        logging.info(
            (f"{xml_id_field} : {id_value} inserted...").encode(
                encoding="ascii", errors="xmlcharrefreplace"
            )
        )
        await notification_function.send_notification(id_value)

def get_xml_data() -> OrderedDict[str, Any]:
    """Return xml data as dictionary. """

    # pull latest PIB from nats: https://pibs.nats.co.uk/operational/pibs/PIB.xml (updated every hour)
    response = requests.get('https://pibs.nats.co.uk/operational/pibs/PIB.xml')
    return xmltodict.parse(response.text)

def get_mongo_credentials() -> tuple[str, str, str, int, str, str]:
    """Return the database secrets. """

    mongo_db_username = os.environ.get("MONGO_USERNAME", "")
    mongo_db_password = os.environ.get("MONGO_PASSWORD","")
    mongo_db_name = os.environ.get("MONGO_INITDB_DATABASE","")
    mongo_db_port = os.environ.get("EXP_PORT", 27017)
    mongo_db_host = os.environ.get("DB_HOST", "")
    mongo_db_collection = os.environ.get("DB_COLLECTION", "")

    return (
        mongo_db_username,
        mongo_db_password,
        mongo_db_name,
        int(mongo_db_port),
        mongo_db_host,
        mongo_db_collection,
    )

coro = run()

if __name__ == "__main__":
    asyncio.run(coro)