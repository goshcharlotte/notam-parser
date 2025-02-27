""" Tests for database and projections."""


import dotenv
import shutil
import os
import sys
from pymongo import MongoClient # type: ignore
import xmltodict # type: ignore

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import datetime
from pathlib import Path
from unittest.mock import patch

# import lambda_function as database_pop
import parse as parser_function  # noqa: E402


# DOCKER
folder_file = os.path.split(rf"{Path(__file__).parent}/utils/.env")
file_path = Path(os.path.join(Path(folder_file[0]), folder_file[1]))
dotenv.load_dotenv(file_path)

MONGO_INITDB_ROOT_USERNAME = os.getenv("TEST_USER")
MONGO_INITDB_ROOT_PASSWORD = os.getenv("TEST_PASSWORD")
MONGO_DB = os.getenv("TEST_DB")
EXP_PORT = os.getenv("EXP_PORT")
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_COLLECTION = os.environ.get("DB_COLLECTION", "pib")

XML_FOLDER='tests/integration/testXmlFiles/'

client = MongoClient(f'mongodb://{DB_HOST}:{EXP_PORT}/',username=MONGO_INITDB_ROOT_USERNAME,password=MONGO_INITDB_ROOT_PASSWORD)
db = client[f"{MONGO_DB}"]

def test_1_populate_mongodb() -> None:
    """Populate docker database for testing. Only one document created."""

    with patch.object(
        parser_function,
        "get_mongo_credentials",
        return_value=(MONGO_INITDB_ROOT_USERNAME, MONGO_INITDB_ROOT_PASSWORD, MONGO_DB, EXP_PORT, DB_HOST,DB_COLLECTION),
    ):
        with patch.object(
        parser_function,
        "get_xml_data",
        return_value =(read_xmlfile())
        ):
            parser_function.run()

    json_collection = db[f"{DB_COLLECTION}"]

    documents = list(json_collection.find({}))
    total_documents = len(documents)
    assert total_documents == 1

def test_2_populate_mongodb() -> None:
    """Rerun same test file into db. Document count should remain unchanged."""

    with patch.object(
        parser_function,
        "get_mongo_credentials",
        return_value=(MONGO_INITDB_ROOT_USERNAME, MONGO_INITDB_ROOT_PASSWORD, MONGO_DB, EXP_PORT, DB_HOST,DB_COLLECTION),
    ):
        with patch.object(
        parser_function,
        "get_xml_data",
        return_value =(read_xmlfile())
        ):
            parser_function.run()

    json_collection = db[f"{DB_COLLECTION}"]

    documents = list(json_collection.find({}))
    total_documents = len(documents)
    assert total_documents == 1

def read_xmlfile():
    """ Read test xml file"""
    for file_name in os.listdir(XML_FOLDER):
        if file_name.endswith('.xml'):
            file_path = os.path.join(XML_FOLDER, file_name)
            print(f"Reading xml file: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as file:
                #convert xml file to python dictionary
                data = xmltodict.parse(file.read())
                return data


def create_db_collection():
    """Create collection if not present"""

    filter = {"name": DB_COLLECTION}
    if(len(db.get_collection(filter=filter)) <= 0):
        # Collection
        db.create_collection(DB_COLLECTION, codec_options=None, read_preference=None, write_concern=None, read_concern=None, session=None, check_exists=True)
