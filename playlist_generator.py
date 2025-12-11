import os
from collections import defaultdict
from typing import Iterable

import pandas as pd
import requests

API_KEY = os.getenv("LASTFM_API_KEY", "b5befec30db2e1875c0bbf5b9757d4b2")
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


def select_top_tracks(top_tracks: pd.DataFrame, sample_size: int = 10) -> pd.DataFrame:
    """Return a reproducible sample of the user's top tracks."""

    if top_tracks.empty:
        raise RuntimeError("No top tracks available to sample.")

    chosen_size = min(len(top_tracks), sample_size)
    return top_tracks.sample(n=chosen_size, random_state=42)[["Utwór", "Artysta"]]


def generate_recommendations(
    top_tracks: pd.DataFrame,
    max_recommendations: int = 20,
    per_artist_limit: int = 2,
) -> Iterable[dict]:
    """Generate recommendation entries based on similar artists."""

    recommendations: list[dict] = []
    artist_counts: defaultdict[str, int] = defaultdict(int)
    unique_artists = top_tracks["Artysta"].unique().tolist()
    seen_tracks = set(track.lower() for track in top_tracks["Utwór"].astype(str))

    for artist in unique_artists:
        if len(recommendations) >= max_recommendations:
            break

        for sim_artist in fetch_similar_artists(artist):
            for track in fetch_artist_top_tracks(sim_artist):
                track_name = track.get("name", "").strip()
                if not track_name:
                    continue

                track_key = track_name.lower()
                if track_key in seen_tracks or artist_counts[sim_artist] >= per_artist_limit:
                    continue

                recommendations.append({"Utwór": track_name, "Artysta": sim_artist})
                seen_tracks.add(track_key)
                artist_counts[sim_artist] += 1

                if len(recommendations) >= max_recommendations:
                    break
            if len(recommendations) >= max_recommendations:
                break

    return recommendations


def build_playlist() -> pd.DataFrame:
    """Create a playlist by mixing top tracks with recommendations."""

    top_tracks_df = get_top_tracks()
    chosen_top = select_top_tracks(top_tracks_df, sample_size=10)
    recs = list(generate_recommendations(top_tracks_df, max_recommendations=20))
    rec_df = pd.DataFrame(recs)

    return pd.concat([chosen_top, rec_df], ignore_index=True)


if __name__ == "__main__":
    playlist_df = build_playlist()
    playlist_df.to_csv("playlist_lastfm.csv", index=False)
    print(playlist_df)
