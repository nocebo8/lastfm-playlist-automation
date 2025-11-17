import os
from collections import defaultdict

import pandas as pd
import requests

API_KEY = "b5befec30db2e1875c0bbf5b9757d4b2"
USER = "NostromoRock"
PERIOD = os.getenv("PERIOD", "6month")
LIMIT = 80
API_URL = "http://ws.audioscrobbler.com/2.0/"


def call_lastfm(params: dict) -> dict:
    """Call the Last.fm API and return JSON or raise a helpful error."""

    default_params = {
        "api_key": API_KEY,
        "format": "json",
    }
    response = requests.get(API_URL, params={**default_params, **params}, timeout=30)
    response.raise_for_status()
    payload = response.json()

    if "error" in payload:
        raise RuntimeError(
            f"Last.fm API error {payload['error']}: {payload.get('message', 'Unknown error')}"
        )

    return payload


def get_top_tracks() -> pd.DataFrame:
    """Return the user's top tracks for the configured period."""

    data = call_lastfm(
        {
            "method": "user.gettoptracks",
            "user": USER,
            "period": PERIOD,
            "limit": LIMIT,
        }
    )

    top_tracks = data.get("toptracks", {}).get("track")
    if not top_tracks:
        raise RuntimeError(
            "Last.fm did not return any top tracks. "
            "Verify that the user exists and the PERIOD has listening data."
        )

    if isinstance(top_tracks, dict):
        top_tracks = [top_tracks]

    return pd.DataFrame(
        [
            {
                "Utwór": track["name"],
                "Artysta": track["artist"]["name"],
                "Scrobbles": int(track["playcount"]),
            }
            for track in top_tracks
        ]
    )


def fetch_similar_artists(artist: str) -> list[str]:
    """Return the artist and up to two similar artists."""

    similar_response = call_lastfm(
        {
            "method": "artist.getsimilar",
            "artist": artist,
            "limit": 2,
        }
    )

    similar = [artist]
    similar_data = similar_response.get("similarartists", {}).get("artist", [])
    similar.extend([entry["name"] for entry in similar_data[:2]])
    return similar


def fetch_artist_top_tracks(artist: str) -> list[dict]:
    """Return up to five top tracks for the given artist."""

    tracks_response = call_lastfm(
        {
            "method": "artist.gettoptracks",
            "artist": artist,
            "limit": 5,
        }
    )

    tracks = tracks_response.get("toptracks", {}).get("track", [])
    if isinstance(tracks, dict):
        tracks = [tracks]
    return tracks


top_tracks_df = get_top_tracks()

# Losowe 1/3 z tych utworów
chosen_top = top_tracks_df.sample(n=10, random_state=42)

# 2/3 rekomendacje: max 2 utwory na artystę, także podobni artyści
recommendations = []
artist_counts = defaultdict(int)
unique_artists = top_tracks_df["Artysta"].unique().tolist()

for artist in unique_artists:
    if len(recommendations) >= 20:
        break

    for sim_artist in fetch_similar_artists(artist):
        for track in fetch_artist_top_tracks(sim_artist):
            if (
                track["name"] not in top_tracks_df["Utwór"].values
                and artist_counts[sim_artist] < 2
            ):
                recommendations.append({
                    "Utwór": track["name"],
                    "Artysta": sim_artist,
                })
                artist_counts[sim_artist] += 1
                if len(recommendations) >= 20:
                    break
        if len(recommendations) >= 20:
            break

rec_df = pd.DataFrame(recommendations)

playlist_df = pd.concat([chosen_top[["Utwór", "Artysta"]], rec_df], ignore_index=True)
playlist_df.to_csv("playlist_lastfm.csv", index=False)
print(playlist_df)
