from typing import Any, OrderedDict
from pymongo import MongoClient  # type: ignore
import pymongo
from bson.json_util import dumps
from bson.json_util import loads

import json
import logging
import os
import requests
import xmltodict  # type: ignore
from dotenv import load_dotenv

load_dotenv()


def send_notification():

    mongo_db_username, mongo_db_password, mongo_db_name, mongo_db_port, mongo_db_host, mongo_db_collection = get_mongo_credentials()

    # connect to the database
    uri = f"mongodb://{mongo_db_username}:{mongo_db_password}@{mongo_db_host}:{mongo_db_port}/{mongo_db_name}?authSource=admin"
    client = MongoClient(uri)
    db = client[f"{mongo_db_name}"]

    # Collection
    json_collection = db[f"{mongo_db_collection}"]

    # latest document inserted for projection
    cursor = json_collection.find({}).sort({"_id": -1}).limit(1)

    apt_code = 'LGW'

    # print(doc[0])
    json_doc = loads(dumps(cursor))
    notification_validity = json_doc[0].get('AreaPIBHeader')['Validity']
    notification_issued_date = json_doc[0].get('AreaPIBHeader')['Issued']
    notification_disclaimer = json_doc[0].get('MeteoDisclaimer')
    pib_id = json_doc[0].get('@PIBId')
    # print(json_doc[0].get('@PIBType'))
    # print(json_doc[0].get('AreaPIBHeader')['Validity'])

    # print(f"pib_id: {pib_id}    {notification_issued_date}")
    # print(
    #     f"ValidFrom: {notification_validity['ValidFrom']}  => {notification_validity['ValidTo']}")
    # print(notification_disclaimer)

    # get_projection(json_collection, 'LGW')

# def get_projection(json_collection : Any, apt_code: str):
#     """Get notam warnings based on airport IATA code """

    filtered_airport = json_collection.aggregate([
        {'$unwind': "$AreaPIBHeader.AerodromeList.Aerodrome"},
        {'$match': {
            "@PIBId": pib_id,
            'AreaPIBHeader.AerodromeList.Aerodrome.IATA':  {'$eq': apt_code}
        }},
        {'$replaceRoot': {'newRoot': "$AreaPIBHeader.AerodromeList.Aerodrome"}}
    ])

    json_ica0_doc = loads(dumps(filtered_airport))
    icao_code = json_ica0_doc[0].get('FIRList')['FIR']['ICAO']  # expected EGTT
    aerodrome_code = json_ica0_doc[0]['Code']  # expected EGKK

    # get notams
    airport_notams = json_collection.aggregate([
        {'$match': {
            "@PIBId": pib_id,
            'FIRSection.ICAO': {'$eq': icao_code}  # FIR code //param
        }},
        {
            '$unwind': '$FIRSection',
        },
        {
            # filter messages here
            '$match': {
                'FIRSection.ADSection.Code': aerodrome_code  # APT CODE
            },
        },
        {
            '$project': {
                'result': {
                    '$filter': {
                        'input': '$FIRSection.ADSection',
                        'as': 'message',
                        'cond': {'$eq': ['$$message.Code',  aerodrome_code]}
                    }
                }
            }
        },
    ])

    json_notams_doc = loads(dumps(airport_notams))
    notam_list = json_notams_doc[0]['result'][0].get('NotamList')['Notam']



def get_mongo_credentials() -> tuple[str, str, str, int, str, str]:
    """Return the database secrets. """

    mongo_db_username = os.environ.get("MONGO_USERNAME", "")
    mongo_db_password = os.environ.get("MONGO_PASSWORD", "")
    mongo_db_name = os.environ.get("MONGO_INITDB_DATABASE", "")
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


if __name__ == "__main__":
    send_notification()
