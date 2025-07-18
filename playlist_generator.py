import requests
import pandas as pd
import random
from collections import defaultdict

API_KEY = "b5befec30db2e1875c0bbf5b9757d4b2"
USER = "NostromoRock"
PERIOD = "6month"
LIMIT = 30

# Pobierz top utwory z ostatnich 180 dni
url = f"http://ws.audioscrobbler.com/2.0/?method=user.gettoptracks&user={USER}&api_key={API_KEY}&period={PERIOD}&limit={LIMIT}&format=json"
response = requests.get(url)
data = response.json()

top_tracks = data['toptracks']['track']
top_tracks_df = pd.DataFrame([{
    'Utwór': track['name'],
    'Artysta': track['artist']['name'],
    'Scrobbles': int(track['playcount'])
} for track in top_tracks])

# Losowe 1/3 z tych utworów
chosen_top = top_tracks_df.sample(n=10, random_state=42)

# 2/3 rekomendacje: max 2 utwory na artystę, także podobni artyści
recommendations = []
artist_counts = defaultdict(int)
unique_artists = top_tracks_df['Artysta'].unique().tolist()

for artist in unique_artists:
    if len(recommendations) >= 20:
        break
    # Dodaj podobnych artystów (2 podobnych + oryginał)
    sim_url = f"http://ws.audioscrobbler.com/2.0/?method=artist.getsimilar&artist={artist}&api_key={API_KEY}&format=json&limit=2"
    sim_resp = requests.get(sim_url).json()
    similar_artists = [artist]
    if "similarartists" in sim_resp and "artist" in sim_resp["similarartists"]:
        similar_artists += [a['name'] for a in sim_resp["similarartists"]["artist"][:2]]

    for sim_artist in similar_artists:
        rec_url = f"http://ws.audioscrobbler.com/2.0/?method=artist.gettoptracks&artist={sim_artist}&api_key={API_KEY}&limit=5&format=json"
        rec_response = requests.get(rec_url).json()
        if "toptracks" in rec_response and "track" in rec_response["toptracks"]:
            tracks = rec_response['toptracks']['track']
            if isinstance(tracks, dict):
                tracks = [tracks]
            for track in tracks:
                if (
                    track['name'] not in top_tracks_df['Utwór'].values
                    and artist_counts[sim_artist] < 2
                ):
                    recommendations.append({
                        'Utwór': track['name'],
                        'Artysta': sim_artist
                    })
                    artist_counts[sim_artist] += 1
                    if len(recommendations) >= 20:
                        break
            if len(recommendations) >= 20:
                break
        if len(recommendations) >= 20:
            break

rec_df = pd.DataFrame(recommendations)

playlist_df = pd.concat([chosen_top[['Utwór', 'Artysta']], rec_df], ignore_index=True)
playlist_df.to_csv('playlist_lastfm.csv', index=False)
print(playlist_df)
