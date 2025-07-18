import requests
import pandas as pd
import random

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

# 2/3 rekomendacje na podstawie najpopularniejszych artystów
top_artists = top_tracks_df['Artysta'].unique().tolist()
recommendations = []
for artist in top_artists:
    url2 = f"http://ws.audioscrobbler.com/2.0/?method=artist.gettoptracks&artist={artist}&api_key={API_KEY}&limit=10&format=json"
    resp = requests.get(url2).json()
    for tr in resp['toptracks']['track']:
        if tr['name'] not in top_tracks_df['Utwór'].values:
            recommendations.append({'Utwór': tr['name'], 'Artysta': artist})
        if len(recommendations) >= 20:
            break
    if len(recommendations) >= 20:
        break
rec_df = pd.DataFrame(recommendations)

playlist_df = pd.concat([chosen_top[['Utwór', 'Artysta']], rec_df])
playlist_df.to_csv('playlist_lastfm.csv', index=False)
print(playlist_df)
