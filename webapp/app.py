from flask import Flask, render_template

from typing import Any, OrderedDict
from pymongo import MongoClient  # type: ignore
import pymongo
from bson.json_util import dumps
from bson.json_util import loads

import logging
import os
from dotenv import load_dotenv

import folium # type: ignore
import datetime


app = Flask(__name__)


@app.route('/')
def index():
    return 'Hello world'


@app.route('/notam/<notam_id>')
def notam(notam_id):

    apt_code = 'LGW'  # hardcoded IATA airport code    
    apt_coordinates = [51.19,-0.24]  # '51.1537° N, 0.1821° W'
    # hardcoded coordinates for LGW not from notam 51.19, -0.24
    pib_id = notam_id

    mongo_db_username, mongo_db_password, mongo_db_name, mongo_db_port, mongo_db_host, mongo_db_collection = get_mongo_credentials()

    # connect to the database
    uri = f"mongodb://{mongo_db_username}:{mongo_db_password}@{mongo_db_host}:{mongo_db_port}/{mongo_db_name}?authSource=admin"
    client = MongoClient(uri)
    db = client[f"{mongo_db_name}"]

    # Collection
    json_collection = db[f"{mongo_db_collection}"]

    # latest document inserted for projection
    cursor = json_collection.find({}).sort(
        {"_id": -1}).limit(1) if pib_id is None else json_collection.find({'@PIBId': pib_id})
    json_doc = loads(dumps(cursor))

    valid_from = ''
    valid_to = ''
    issued_date = ''
    notam_disclaimer = ''
    if json_doc != []:
        pib_id = json_doc[0].get('@PIBId')
        notam_validity = json_doc[0].get('AreaPIBHeader')['Validity']
        issued_date = datetime.datetime.strftime(datetime.datetime.fromisoformat(
            json_doc[0].get('AreaPIBHeader')['Issued']), "%d %B %Y %X")  # type: ignore
        notam_disclaimer = json_doc[0].get('MeteoDisclaimer')
        valid_from = datetime.datetime.strftime(datetime.datetime.fromisoformat(
            notam_validity['ValidFrom']), "%d %B %Y %X")  # type: ignore
        valid_to = datetime.datetime.strftime(datetime.datetime.fromisoformat(
            notam_validity['ValidTo']), "%d %B %Y %X")  # type: ignore

    filtered_airport = json_collection.aggregate([
        {'$unwind': "$AreaPIBHeader.AerodromeList.Aerodrome"},
        {'$match': {
            "@PIBId": pib_id,
            'AreaPIBHeader.AerodromeList.Aerodrome.IATA':  {'$eq': apt_code}
        }},
        {'$replaceRoot': {'newRoot': "$AreaPIBHeader.AerodromeList.Aerodrome"}}
    ])

    json_ica0_doc = loads(dumps(filtered_airport))
    icao_code = ''
    aerodrome_code = ''

    if json_ica0_doc != []:
        icao_code = json_ica0_doc[0].get(
            'FIRList')['FIR']['ICAO']  # expected EGTT for LGW
        aerodrome_code = json_ica0_doc[0]['Code']  # expected EGKK for LGW

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
    notam_list = []

    if json_notams_doc != []:
        notam_list = json_notams_doc[0]['result'][0].get('NotamList')['Notam']

    print(f'total notifications: {len(notam_list)}')
    logging.info(
        (f"total notifications: {len(notam_list)} ").encode(
            encoding="ascii", errors="xmlcharrefreplace"
        )
    )

    today = datetime.date.today()
    year = today.strftime("%Y")

    return render_template('notam.html', apt_code=apt_code, apt_coordinates=apt_coordinates, notam_id=pib_id, notam_validity_from=valid_from, notam_validity_to=valid_to, notam_issued_date=issued_date, notam_len=len(notam_list), notam_list=notam_list, folium=folium, notam_disclaimer=notam_disclaimer, year=year)


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


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)
