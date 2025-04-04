from flask import Flask, render_template, request

import pandas as pd
import numpy as np

from typing import Any, OrderedDict
from pymongo import MongoClient  # type: ignore
import pymongo
from bson.json_util import dumps
from bson.json_util import loads

import logging
import os
from dotenv import load_dotenv

import folium # type: ignore
import folium.plugins as plugins
import datetime


app = Flask(__name__)

@app.route('/')
def index():
    doc_limit = 20
    mongo_db_username, mongo_db_password, mongo_db_name, mongo_db_port, mongo_db_host, mongo_db_collection = get_mongo_credentials()

    # connect to the database
    uri = f"mongodb://{mongo_db_username}:{mongo_db_password}@{mongo_db_host}:{mongo_db_port}/{mongo_db_name}?authSource=admin"
    client = MongoClient(uri)
    db = client[f"{mongo_db_name}"]

    # Collection
    json_collection = db[f"{mongo_db_collection}"]

    doc_limit = json_collection.count_documents({}) if json_collection.count_documents({}) < doc_limit else doc_limit
    # latest document inserted for projection
    cursor = json_collection.find({}).sort({"_id": -1}).limit(doc_limit)
    json_doc = loads(dumps(cursor))

    notifications =[]
    i = 0
    while i < doc_limit:
        print(i)        
        pib_id = json_doc[i].get('@PIBId')
        notam_validity = json_doc[i].get('AreaPIBHeader')['Validity']
        issued_date = datetime.datetime.strftime(datetime.datetime.fromisoformat(json_doc[i].get('AreaPIBHeader')['Issued']), "%d %B %Y %X")  # type: ignore
        notam_disclaimer = json_doc[i].get('MeteoDisclaimer')
        valid_from = datetime.datetime.strftime(datetime.datetime.fromisoformat(notam_validity['ValidFrom']), "%d %B %Y %X")  # type: ignore
        valid_to = datetime.datetime.strftime(datetime.datetime.fromisoformat(notam_validity['ValidTo']), "%d %B %Y %X")  # type: ignore
        notification_dictionary = {'id' : pib_id, 'issued_date': issued_date, 'valid_from': valid_from, 'valid_to' : valid_to}
        notifications.append(notification_dictionary)
        i += 1

    today = datetime.date.today()
    year = today.strftime("%Y")

    return render_template('home.html', notifications=notifications, notam_disclaimer=notam_disclaimer, year=year)


@app.route('/notam/<notam_id>', methods = ['GET', 'POST'])
def notam(notam_id):

    apt_code = 'GLA'  # hardcoded IATA airport code    GLA    
    # hardcoded coordinates for LGW not from notam 51.19, -0.24
    pib_id = notam_id
    # to convert to meter from nautical miles is 1852 || miles is  1609.344
    miles_conversion=1852

    print(request)
    if request.method == 'POST':
        try:
            print(request.form)
            apt_code = request.form["airport"]
            print(apt_code)
        except Exception as error:
            print(f"ERROR :  {error}")


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
            'FIRList')['FIR']['ICAO']  # expected EGTT for LONDON FIR
        aerodrome_code = json_ica0_doc[0]['Code']  # expected EGKK for LGW

    
    notam_list = get_adsection_notams(icao_code, aerodrome_code, pib_id)
    print(f'total notifications: {len(notam_list)}')
    logging.info(
        (f"total notifications: {len(notam_list)} ").encode(
            encoding="ascii", errors="xmlcharrefreplace"
        )
    )
    warning_notams = get_warning_notams(icao_code, pib_id)
    enroute_notams = get_enroute_notams(icao_code, pib_id)

    today = datetime.date.today()
    year = today.strftime("%Y")

    airports = [None,'GLA', 'LGW'] # list for dropdown
    
    df = pd.read_csv('./static/airports.csv')
    a = df.to_numpy()
    row = np.where(a == apt_code)[0][0]
    apt_coordinates = [df.at[row, 'latitude'], df.at[row, 'longitude']] 

    return render_template('notam.html', airports=airports, miles_conversion=miles_conversion, apt_code=apt_code, apt_coordinates=apt_coordinates, notam_id=pib_id, notam_validity_from=valid_from, notam_validity_to=valid_to, notam_issued_date=issued_date, notam_len=len(notam_list), warning_len=len(warning_notams), enroute_len=len(enroute_notams) ,notam_list=notam_list, warning_list=warning_notams, enroute_list=enroute_notams, map_library=folium, plugins=plugins, notam_disclaimer=notam_disclaimer, year=year, datetime_formatter=datetime.datetime)

def get_adsection_notams(apt_icao:str,aerodrome_code:str , pib_id:str):
    '''Get adsection notams from apt id'''

    mongo_db_username, mongo_db_password, mongo_db_name, mongo_db_port, mongo_db_host, mongo_db_collection = get_mongo_credentials()

    # connect to the database
    uri = f"mongodb://{mongo_db_username}:{mongo_db_password}@{mongo_db_host}:{mongo_db_port}/{mongo_db_name}?authSource=admin"
    client = MongoClient(uri)
    db = client[f"{mongo_db_name}"]

    # Collection
    json_collection = db[f"{mongo_db_collection}"]

    # get notams
    airport_notams = json_collection.aggregate([
        {'$match': {
            "@PIBId": pib_id,
            'FIRSection.ICAO': {'$eq': apt_icao}  # FIR code //param
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
    
    return notam_list

def get_warning_notams(apt_icao:str, pib_id:str):
    '''Get warnings from apt notams from id '''
    
    mongo_db_username, mongo_db_password, mongo_db_name, mongo_db_port, mongo_db_host, mongo_db_collection = get_mongo_credentials()

    # connect to the database
    uri = f"mongodb://{mongo_db_username}:{mongo_db_password}@{mongo_db_host}:{mongo_db_port}/{mongo_db_name}?authSource=admin"
    client = MongoClient(uri)
    db = client[f"{mongo_db_name}"]

    # Collection
    json_collection = db[f"{mongo_db_collection}"]

    # get warnings
    result_notams = json_collection.aggregate([
        {'$match': {
            "@PIBId": pib_id,
            'FIRSection.ICAO':  apt_icao  # FIR code //param apt_icao
        }},
        {
            '$unwind': '$FIRSection',
        },
        {
            # filter messages here
            '$match': {
                'FIRSection.ICAO': apt_icao,
                'FIRSection.Warnings.NotamList.Notam.ItemA' : apt_icao, # City CODE
                #'FIRSection.Warnings.NotamList.Notam.ItemA' : { '$in': [apt_icao]}
            },
        },
        {
            '$project': {
                'Warnings': {
                    '$filter': {
                        'input': "$FIRSection.Warnings.NotamList.Notam",
                        'as': 'message',
                        'cond': { '$eq': [ "$$message.ItemA", apt_icao ] }
                        #'cond': { '$in': [ "$$message.ItemA", [apt_icao] ] }
                    }
                }
            }
        },
    ])

    warning_notams = []
    json_notams_doc = loads(dumps(result_notams))
    if json_notams_doc != []:
        warning_notams = json_notams_doc[0].get('Warnings')
    return warning_notams
    
def get_enroute_notams(apt_icao:str, pib_id:str):
    '''Get en-route notifications from airport notams from id '''
    
    mongo_db_username, mongo_db_password, mongo_db_name, mongo_db_port, mongo_db_host, mongo_db_collection = get_mongo_credentials()

    # connect to the database
    uri = f"mongodb://{mongo_db_username}:{mongo_db_password}@{mongo_db_host}:{mongo_db_port}/{mongo_db_name}?authSource=admin"
    client = MongoClient(uri)
    db = client[f"{mongo_db_name}"]

    # Collection
    json_collection = db[f"{mongo_db_collection}"]

    # get warnings
    result_notams = json_collection.aggregate([
        {'$match': {
            "@PIBId": pib_id,
            'FIRSection.ICAO': {'$eq': apt_icao}  # APT icao
        }},
        {
            '$unwind': '$FIRSection',
        },
        {
            # filter messages here
            '$match': {
                'FIRSection.ICAO': {'$eq': apt_icao}, # APT icao
                'FIRSection.En-route.NotamList.Notam.ItemA' : apt_icao, # APT CODE
            },
        },
        {
            '$project': {
                'EnRoute': {
                    '$filter': {
                        'input': "$FIRSection.En-route.NotamList.Notam",
                        'as': 'message',
                        'cond': { '$eq': [ "$$message.ItemA", apt_icao ] }
                    }
                }
            }
        },
    ])

    enroute_notams = []
    json_notams_doc = loads(dumps(result_notams))
    if json_notams_doc != []:
        enroute_notams = json_notams_doc[0].get('EnRoute')

    return enroute_notams


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
