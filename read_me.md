
# TasteTuner 🎵  
**Music Taste Modeling and Playlist Optimization using Spotify Data**

TasteTuner is a Python-based intelligent playlist generation tool that creates personalized playlists by analyzing a user’s top artists, genres, and audio preferences using the Spotify API. The system models user taste and applies optimization techniques to recommend tracks that balance familiarity and discovery.

---

## Features

- OAuth2-based secure Spotify login
- Fetches top artists, genres, and audio features
- Models music preferences (danceability, energy, valence, etc.)
- Optimizes playlist using Integer Linear Programming
- Recommends diverse new songs not previously listened to
- Automatically creates playlist in your Spotify account

---

## Installation

1. **Clone the repo:**
   ```bash
   git clone https://github.com/yourusername/Taste-Tuner.git
   cd TasteTuner


2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Create `.env` file** with your Spotify developer credentials:

   ```
   SPOTIPY_CLIENT_ID=your_spotify_client_id
   SPOTIPY_CLIENT_SECRET=your_spotify_client_secret
   SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
   ```

4. **Run the script:**

   ```bash
   python3 taste_tuner.py
   ```

---

## Requirements

* Python 3.7+
* Spotify Developer Account ([Create one here](https://developer.spotify.com/dashboard/))
* Required packages:

  * `spotipy`
  * `numpy`
  * `pandas`
  * `python-dotenv`
  * `pulp`

---

## Optimization Logic

TasteTuner assigns scores to candidate tracks based on:

* Artist similarity
* Genre overlap
* Audio feature matching
* Popularity
* Diversity factor

A linear programming model selects the optimal set of tracks based on weighted preferences.

---

## Customization

Weights can be adjusted in `TasteTuner.__init__()`:

```python
self.weights = {
    'artist_match': 0.25,
    'genre_match': 0.25,
    'popularity': 0.2,
    'audio_match': 0.4,
    'diversity': 0.5
}
```

Tune these to create exploratory or mood-based playlists.


## Future Work

* Emotion-aware playlist generation
* Incorporating lyrics and sentiment analysis
* Group-based or collaborative playlist creation
* Reinforcement learning integration for adaptive tuning