import os
import time
from xml.etree.ElementTree import Element, SubElement, tostring

from fastapi import FastAPI, Response
from pymongo import MongoClient


MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
MONGODB_DB = os.getenv("MONGODB_DB", "artist")

app = FastAPI(title="Artist Lineup Service", version="1.0.0")
mongo_client = MongoClient(MONGODB_URL, serverSelectionTimeoutMS=5000)
artists = mongo_client[MONGODB_DB]["artists"]


def init_db() -> None:
    for attempt in range(12):
        try:
            mongo_client.admin.command("ping")
            break
        except Exception:
            if attempt == 11:
                raise
            time.sleep(2)
    artists.create_index("concert_id")
    if artists.count_documents({}) == 0:
        artists.insert_many(
            [
                {
                    "concert_id": "concert-2026-jkt",
                    "artist_name": "Nadin Amizah",
                    "stage_name": "Main Stage",
                    "start_time": "19:00",
                },
                {
                    "concert_id": "concert-2026-jkt",
                    "artist_name": "Hindia",
                    "stage_name": "Main Stage",
                    "start_time": "20:30",
                },
                {
                    "concert_id": "concert-2026-jkt",
                    "artist_name": "Reality Club",
                    "stage_name": "Second Stage",
                    "start_time": "18:15",
                },
            ]
        )


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "artist"}


@app.get("/lineup/{concert_id}.xml")
def lineup_xml(concert_id: str) -> Response:
    root = Element("lineup", attrib={"concertId": concert_id})
    for row in artists.find({"concert_id": concert_id}):
        artist = SubElement(root, "artist")
        SubElement(artist, "name").text = row["artist_name"]
        SubElement(artist, "stage").text = row["stage_name"]
        SubElement(artist, "startTime").text = row["start_time"]
    return Response(tostring(root, encoding="unicode"), media_type="application/xml")


@app.get("/lineup/{concert_id}")
def lineup_json(concert_id: str) -> dict:
    rows = artists.find(
        {"concert_id": concert_id},
        {"_id": 0, "artist_name": 1, "stage_name": 1, "start_time": 1},
    )
    return {"concert_id": concert_id, "artists": list(rows)}
