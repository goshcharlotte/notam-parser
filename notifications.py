from typing import Any, OrderedDict
from pymongo import MongoClient  # type: ignore
import pymongo
from bson.json_util import dumps
from bson.json_util import loads

import asyncio
import logging
import os
import mailslurp_client
from mailslurp_client import CreateInboxDto
from dotenv import load_dotenv


from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import folium
from nicegui import ui
from pyproj import crs
import geopandas as gpd
import matplotlib.pyplot as plt

load_dotenv()

async def send_notification(pib_id=None):
    ''' Isolate notam notification by airport for emails'''

    apt_code = 'LGW' ## hardcoded IATA airport code

    mongo_db_username, mongo_db_password, mongo_db_name, mongo_db_port, mongo_db_host, mongo_db_collection = get_mongo_credentials()

    # connect to the database
    uri = f"mongodb://{mongo_db_username}:{mongo_db_password}@{mongo_db_host}:{mongo_db_port}/{mongo_db_name}?authSource=admin"
    client = MongoClient(uri)
    db = client[f"{mongo_db_name}"]

    # Collection
    json_collection = db[f"{mongo_db_collection}"]

    # latest document inserted for projection
    cursor = json_collection.find({}).sort({"_id": -1}).limit(1) if pib_id is None else json_collection.find({'@PIBId' : pib_id})
    json_doc = loads(dumps(cursor))
    pib_id = json_doc[0].get('@PIBId')
    notam_validity = json_doc[0].get('AreaPIBHeader')['Validity']
    notam_issued_date = json_doc[0].get('AreaPIBHeader')['Issued']
    notam_disclaimer = json_doc[0].get('MeteoDisclaimer')

    filtered_airport = json_collection.aggregate([
        {'$unwind': "$AreaPIBHeader.AerodromeList.Aerodrome"},
        {'$match': {
            "@PIBId": pib_id,
            'AreaPIBHeader.AerodromeList.Aerodrome.IATA':  {'$eq': apt_code}
        }},
        {'$replaceRoot': {'newRoot': "$AreaPIBHeader.AerodromeList.Aerodrome"}}
    ])

    json_ica0_doc = loads(dumps(filtered_airport))
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
    notam_list = json_notams_doc[0]['result'][0].get('NotamList')['Notam']

    print(f'total notifications: {len(notam_list)}')
    await send_email(notam_validity,notam_issued_date,notam_disclaimer, notam_list)


async def send_email(notam_validity: Any,notam_issued_date: str,notam_disclaimer: str, notam_list: Any):
    '''Send notams as html email'''

    api_key = os.environ.get('MAIL_API_KEY')

    m = folium.Map(location=[32.3, 295.21], zoom_start=10, control_scale=True) ##  hardcoded location
    # with ui.card():
    #     map_width = 600
    #     map_height = 300
    #     m = folium.Map(location=[32.3, 295.21], width=map_width, height=map_height)
    #     m.get_root().width = f"{map_width}px"
    #     m.get_root().height = f"{map_height}px"
    #     iframe = m.get_root()._repr_html_()
    #     ui.html(iframe).classes("w-full h-full")

    #" 5058 N 00209 W"

    # Send the email
    configuration = mailslurp_client.Configuration()
    configuration.api_key['x-api-key'] = api_key
    with mailslurp_client.ApiClient(configuration) as api_client:
        # create an inbox
        inbox_controller = mailslurp_client.InboxControllerApi(api_client)
        inbox = inbox_controller.create_inbox()

        # create email html body
        x = 1 # mailslurp_client inbox limit to 10 emails
        for notam in notam_list:
            subject = "Notam HTML Email without Attachment"
            html = f"""\
            <html>
            <body>
                <p>notam validity: {notam_validity['ValidFrom']} to {notam_validity['ValidTo']}</p>
                <p>notam issued date:{notam_issued_date}</p>
                <div>                
                    <p>{notam_disclaimer}</p>
                </div>
                <div>
                    <p>Coordinates: {notam.get('Coordinates')}</p>
                    <p>Details: {notam.get('ItemE')}</p>
                    <br>
                </div>
                <div style='width: 30em; height: 10em;'>{m.get_root()._repr_html_()}</div>
            </body>
            </html>
            """

            send_options = mailslurp_client.SendEmailOptions(
                to=[os.environ.get('EMAIL_ADRESS')],
                subject=subject,
                body=html
            )

            # mailslurp_client inbox limit to 10 emails
            if x <= 10: 
                sent = inbox_controller.send_email_and_confirm(
                    inbox_id=inbox.id, send_email_options=send_options
                )

                logging.info(
                    (f"email sent for notam dated: {sent.sent_at}").encode(
                        encoding="ascii", errors="xmlcharrefreplace"
                    )
                )
                x = x + 1
                print(f'email sent : {sent.sent_at}')


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


coro = send_notification()

if __name__ == "__main__":
    asyncio.run(coro)
