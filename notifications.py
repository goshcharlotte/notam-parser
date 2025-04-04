import time
from typing import Any, OrderedDict
from pymongo import MongoClient  # type: ignore
import pymongo
from bson.json_util import dumps
from bson.json_util import loads

import asyncio
import logging
import os
from dotenv import load_dotenv


from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import datetime
import brevo_python 

import brevo_python
from brevo_python.rest import ApiException
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException


load_dotenv()

async def send_notification(pib_id=None):
    ''' Isolate notam notification by airport for emails'''

    apt_code = 'GLA' ## hardcoded IATA airport code

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
        'FIRList')['FIR']['ICAO']  # expected EGTT for LONDON FIR
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
    await send_email(pib_id,apt_code, notam_validity,notam_issued_date,notam_disclaimer, notam_list)


async def send_email(pib_id: str, apt_code: str, notam_validity: Any,notam_issued_date: str,notam_disclaimer: str, notam_list: Any):
    '''Send notams as html email'''

    api_key = os.environ.get('MAIL_API_KEY')

    # Send the email
    configuration = mailslurp_client.Configuration()
    configuration.api_key['x-api-key'] = api_key
    email_style = """<style>
    @media screen and (max-width: 600px) {
        .content {
            width: 100% !important;
            display: block !important;
            padding: 10px !important;
        }
        .header, .body, .footer {
            padding: 20px !important;
        }
    }
    </style>"""
    today = datetime.date.today()
    year = today.strftime("%Y")
    issued_date = datetime.datetime.fromisoformat(notam_issued_date)
    subject = f"{apt_code} Notam {issued_date.strftime('%d/%m/%Y, %H:%M:%S')}"
    print(subject)


    html = f"""\
    <!DOCTYPE html>
    <html lang='en'>
        <head>
            <meta charset='UTF-8'>
            <meta name='viewport' content='width=device-width, initial-scale=1.0'>
            <link rel='preconnect' href='https://fonts.googleapis.com'>
            <link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>
            <link href='https://fonts.googleapis.com/css2?family=Poppins:ital,wght@0,100;0,200;0,300;0,400;0,500;0,600;0,700;0,800;0,900;1,100;1,200;1,300;1,400;1,500;1,600;1,700;1,800;1,900&display=swap' rel='stylesheet'>
            <title>{subject}</title>
        </head>
        <body style='font-family: "Poppins", Arial, sans-serif;'>
            <table width='100%' border='0' cellspacing='0' cellpadding='0'>
                <tr>
                    <td align='center' style='padding: 20px;'>
                        <table class='content' width='600' border='0' cellspacing='0' cellpadding='0' style='border-collapse: collapse; border: 1px solid #cccccc;'>
                            <!-- Header -->
                            <tr>
                                <td class='header' style='background-color: #345C72; padding: 40px; text-align: center; color: white; font-size: 24px;'>
                                {subject}
                                </td>
                            </tr>

                            <tr  class='body' style='padding-top: 30px; padding-bottom: 30px; margin-top: 10px; margin-bottom: 10px;'>
                                <td style='padding-top: 30px; padding-bottom: 30px; margin-top: 10px; margin-bottom: 10px;'>
                                <a href='http://localhost:5002/notam/{pib_id}'>Full notifications for {apt_code} airport</a>
                                </td>
                            </tr>

                            <!-- Body -->

                            <!-- Call to action Button -->

                            <!-- Footer -->
                            <tr>
                                <td class='footer' style='background-color: #333333; padding: 40px; text-align: center; color: white; font-size: 14px;'>
                                {notam_disclaimer}
                                <br><br>
                                Copyright &copy; {year} | AndDigital
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
    </html>
    """

    brevo_api_key = os.environ.get('BREVO_API')
    # Configure API key authorization: api-key
    configuration = brevo_python.Configuration()
    configuration.api_key['api-key'] = brevo_api_key
    # Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
    # configuration.api_key_prefix['api-key'] = 'Bearer'
    # Configure API key authorization: partner-key
    configuration = brevo_python.Configuration()
    configuration.api_key['partner-key'] = brevo_api_key
    # Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
    # configuration.api_key_prefix['partner-key'] = 'Bearer'
    # api_instance = brevo_python.AccountApi(brevo_python.ApiClient(configuration))
    try:
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] =  brevo_api_key
        # Get your account information, plan and credits details
        to= [{"email":'xxxx@and.digital',"name":"Jane Doe"}]
        ##bcc= [{"email":'xxx@and.digital',"name":"Jane Doe"}] 
        ##cc= [{"email":'xxx@and.digital',"name":"Jane Doe"}] 
        ##reply_to= [{"email":'xxx@and.digital',"name":"Jane Doe"}]
        headers = {"Some-Custom-Name":"unique-id-1234"}

        email_api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
        subject = subject
        sender = {"name":"APT Notam","email":"xxx@and.digital"}
        html_content = html
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(to=to,
        headers=headers, html_content=html_content, sender=sender, subject=subject) # SendSmtpEmail | Values to send a transactional email
        email_api_response = email_api_instance.send_transac_email(send_smtp_email)
        print(email_api_response)

    except ApiException as e:
        print("Exception when calling AccountApi->get_account: %s\n" % e)


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
