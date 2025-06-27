import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
import pandas as pd
import numpy as np
from pulp import *
import json
from typing import List, Dict, Tuple
import time
import random
import string

class TasteTuner:
    def __init__(self):
        load_dotenv()
        
        # authentication with cache handling
        self.auth_manager = SpotifyOAuth(
            scope=' '.join([
                'user-library-read',
                'user-top-read',
                'playlist-modify-public',
                'playlist-read-private',
                'playlist-modify-private',
                'user-read-private',
                'user-read-email'
            ]),
            redirect_uri='http://127.0.0.1:8888/callback',
            cache_path='.spotify_cache',
            open_browser=True
        )
        
        # Initialize Spotify client
        self.sp = spotipy.Spotify(auth_manager=self.auth_manager)
        
        # Verify authentication
        try:
            user = self.sp.current_user()
            print(f"Authenticated as: {user['display_name']}")
        except Exception as e:
            print(f"Authentication error: {str(e)}")
            raise
        
        # Initialize user data
        self.user_top_artists = {}
        self.user_top_genres = {}
        self.user_audio_preferences = {}
        
        # Weights for different factors
        # self.weights = {
        #     'artist_match': -1,  # Reduced to allow more exploration
        #     'genre_match': 0.15,   # Genre consistency is important
        #     'popularity': 0.05,    # Reduced to allow more exploration
        #     'audio_match': 0.5,   # Audio features matching
        #     'diversity': 0.45      # Encourage diverse recommendations
        # }
        # safe, familiar playlists? Increase artist_match to 0, genre_match to 0.3, reduce diversity.
        # exploratory playlists with new artists? Make artist_match = -1.0, diversity = 0.5, popularity = 0.0.
        # emotionally consistent playlists (e.g., for mood)? Boost audio_match = 0.7, reduce diversity = 0.2.
        
        self.weights = {
            'artist_match': 0.25,   # Allow repeated artists if very relevant
            'genre_match': 0.25,     # Maintain genre identity
            'popularity': 0.2,      # Slight push toward popular songs
            'audio_match': 0.4,     # Important for "sound" feel
            'diversity': 0.5        # Encourage newness and variety
        }

    def fetch_user_data(self):
        """Fetch and cache user's music preferences"""
        try:
            print("Fetching user data...")
            
            # Get user's top artists
            print("Fetching top artists...")
            top_artists = self.sp.current_user_top_artists(limit=50, time_range='medium_term')
            
            if not top_artists['items']:
                print("No top artists found, fetching followed artists...")
                followed = self.sp.current_user_followed_artists(limit=20)
                artist_items = followed['artists']['items'] if 'artists' in followed else []
            else:
                artist_items = top_artists['items']
            
            # Process artists and genres
            self.user_top_artists = {}
            self.user_top_genres = {}
            
            for artist in artist_items:
                self.user_top_artists[artist['id']] = {
                    'name': artist['name'],
                    'popularity': artist['popularity']
                }
                for genre in artist['genres']:
                    self.user_top_genres[genre] = self.user_top_genres.get(genre, 0) + 1
            
            print(f"Found {len(self.user_top_artists)} artists and {len(self.user_top_genres)} genres")
            
        except Exception as e:
            print(f"Error fetching user data: {str(e)}")
            raise

    def calculate_artist_match(self, track: Dict) -> float:
        """Calculate artist similarity score"""
        for artist in track['artists']:
            if artist['id'] in self.user_top_artists:
                return 1.0
        return 0.0

    def calculate_genre_match(self, track: Dict) -> float:
        """Calculate genre similarity score"""
        try:
            artist = self.sp.artist(track['artists'][0]['id'])
            artist_genres = set(artist['genres'])
            user_genres = set(self.user_top_genres.keys())
            
            if not user_genres or not artist_genres:
                return 0.0
                
            return len(artist_genres.intersection(user_genres)) / len(user_genres)
        except:
            return 0.0

    def calculate_popularity_score(self, track: Dict) -> float:
        """Calculate popularity score (0-1)"""
        return track['popularity'] / 100.0

    def get_audio_features(self, track_ids):
        """Get audio features for a list of tracks"""
        features = []
        for track_id in track_ids:
            try:
                # Get features one track at a time
                time.sleep(0.1)  # Add small delay between requests
                feature = self.sp.audio_features(track_id)
                if feature and feature[0]:
                    features.append(feature[0])
            except Exception as e:
                print(f"Error getting audio features for track {track_id}: {str(e)}")
                continue
        return features

    def get_track_analysis(self, track_id):
        """Get detailed track analysis"""
        try:
            time.sleep(0.1)  # Add small delay between requests
            return self.sp.audio_analysis(track_id)
        except Exception as e:
            print(f"Error getting track analysis for {track_id}: {str(e)}")
            return None

    def calculate_audio_preference(self):
        """Calculate user's audio feature preferences from top tracks"""
        print("Analyzing your music preferences...")
        
        # Try different time ranges if one fails
        for time_range in ['short_term', 'medium_term', 'long_term']:
            try:
                top_tracks = self.sp.current_user_top_tracks(limit=100, time_range=time_range)
                if top_tracks['items']:
                    track_ids = [track['id'] for track in top_tracks['items']]
                    features = self.get_audio_features(track_ids)
                    if features:
                        break
            except Exception as e:
                print(f"Error getting top tracks for {time_range}: {str(e)}")
                continue
        
        # If we couldn't get top tracks, try saved tracks
        if not features:
            try:
                saved_tracks = self.sp.current_user_saved_tracks(limit=100)
                track_ids = [item['track']['id'] for item in saved_tracks['items']]
                features = self.get_audio_features(track_ids)
            except Exception as e:
                print(f"Error getting saved tracks: {str(e)}")
        
        # If we still don't have features, return default values
        if not features:
            print("Could not get audio features, using default values")
            self.user_audio_preferences = {
                'danceability': 0.5,
                'energy': 0.5,
                'valence': 0.5,
                'instrumentalness': 0.1,
                'acousticness': 0.3,
                'tempo': 120.0
            }
            return
        
        # Calculate average preferences
        self.user_audio_preferences = {
            'danceability': np.mean([f['danceability'] for f in features]),
            'energy': np.mean([f['energy'] for f in features]),
            'valence': np.mean([f['valence'] for f in features]),
            'instrumentalness': np.mean([f['instrumentalness'] for f in features]),
            'acousticness': np.mean([f['acousticness'] for f in features]),
            'tempo': np.mean([f['tempo'] for f in features])
        }
        
        print("Audio preferences analyzed:")
        for feature, value in self.user_audio_preferences.items():
            print(f"  {feature}: {value:.2f}")

    def calculate_audio_match(self, track_features, user_prefs):
        """Calculate how well a track's audio features match user preferences"""
        if not track_features or not user_prefs:
            return 0.0
            
        # Calculate normalized Euclidean distance for each feature
        distances = []
        weights = {
            'danceability': 1.0,
            'energy': 1.0,
            'valence': 0.8,
            'instrumentalness': 0.5,
            'acousticness': 0.7
        }
        
        for feature, weight in weights.items():
            if feature in track_features and feature in user_prefs:
                distance = abs(track_features[feature] - user_prefs[feature]) * weight
                distances.append(distance)
        
        if not distances:
            return 0.0
            
        # Convert distance to similarity score (1 - normalized distance)
        avg_distance = np.mean(distances)
        return 1.0 - min(avg_distance, 1.0)

    def get_random_search_term(self) -> str:
        """Generate a random search term for Spotify search"""
        # List of common letters to start searches with
        letters = list(string.ascii_lowercase) + ['%'] # '%' is a wildcard in Spotify search
        # Get a random letter
        return random.choice(letters)

    def get_random_tracks(self, num_tracks: int = 100) -> List[Dict]:
        """Get random tracks using Spotify search with random terms"""
        print("\nFetching random tracks...")
        random_tracks = []
        seen_ids = set()
        
        while len(random_tracks) < num_tracks:
            try:
                # Get a random search term
                search_term = self.get_random_search_term()
                
                # Random offset to get different results each time
                offset = random.randint(0, 1000)
                
                # Search for tracks
                results = self.sp.search(
                    q=search_term,
                    type='track',
                    limit=50,  # Maximum allowed by Spotify API
                    offset=offset
                )
                
                if not results['tracks']['items']:
                    continue
                
                # Add unique tracks
                for track in results['tracks']['items']:
                    if track['id'] not in seen_ids:
                        seen_ids.add(track['id'])
                        random_tracks.append(track)
                        print(f"Added random track: {track['name']} by {track['artists'][0]['name']}")
                        
                        if len(random_tracks) >= num_tracks:
                            break
                            
                time.sleep(0.1)  # Add small delay between requests
                
            except Exception as e:
                print(f"Error during random track search: {str(e)}")
                time.sleep(1)  # Longer delay if we hit an error
                continue
        
        return random_tracks

    def get_diverse_tracks(self):
        """Get a diverse set of random tracks"""
        print("\nGathering random tracks...")
        return self.get_random_tracks(100)  # Get 100 random tracks

    def optimize_playlist(self, candidate_tracks: List[Dict], playlist_size: int = 20) -> List[str]:
        """Optimize playlist using Integer Linear Programming"""
        if not candidate_tracks:
            return []
            
        # Create the optimization problem
        prob = LpProblem("PlaylistOptimization", LpMaximize)
        
        # Decision variables (1 if track is selected, 0 otherwise)
        track_vars = LpVariable.dicts("track",
                                    ((i) for i in range(len(candidate_tracks))),
                                    0, 1, LpInteger)
        
        # Calculate scores for each track
        track_scores = []
        for track in candidate_tracks:
            artist_score = self.calculate_artist_match(track)
            genre_score = self.calculate_genre_match(track)
            popularity_score = self.calculate_popularity_score(track)
            
            total_score = (
                self.weights['artist_match'] * artist_score +
                self.weights['genre_match'] * genre_score +
                self.weights['popularity'] * popularity_score
            )
            track_scores.append(total_score)
        
        # Objective function
        prob += lpSum([track_vars[i] * track_scores[i] for i in range(len(candidate_tracks))])
        
        # Constraints
        # Playlist size constraint
        prob += lpSum([track_vars[i] for i in range(len(candidate_tracks))]) == playlist_size
        
        # Solve the problem
        prob.solve()
        
        # Get selected tracks
        selected_tracks = []
        for i in range(len(candidate_tracks)):
            if track_vars[i].value() == 1:
                selected_tracks.append(candidate_tracks[i]['id'])
                
        return selected_tracks

    def create_optimized_playlist(self, playlist_size: int = 20) -> str:
        """Create an optimized playlist based on user's taste"""
        try:
            # Fetch user data if not already cached
            if not self.user_top_artists:
                self.fetch_user_data()
            
            print("Creating optimized playlist...")
            
            # Get diverse candidate tracks
            candidate_tracks = self.get_diverse_tracks()
            
            if not candidate_tracks:
                raise Exception("No candidate tracks found")
            
            # Calculate scores for optimization
            track_scores = []
            for track in candidate_tracks:
                # Basic scores
                artist_score = self.calculate_artist_match(track)
                genre_score = self.calculate_genre_match(track)
                popularity_score = self.calculate_popularity_score(track)
                
                # Diversity score (favor less popular tracks and new artists)
                diversity_score = 1.0 - (artist_score * 0.5 + popularity_score * 0.5)
                
                # Calculate total score
                total_score = (
                    self.weights['artist_match'] * artist_score +
                    self.weights['genre_match'] * genre_score +
                    self.weights['popularity'] * popularity_score +
                    self.weights['diversity'] * diversity_score
                )
                track_scores.append(total_score)
                
                print(f"\nScores for {track['name']}:")
                print(f"  Artist match: {artist_score:.2f}")
                print(f"  Genre match: {genre_score:.2f}")
                print(f"  Popularity: {popularity_score:.2f}")
                print(f"  Diversity: {diversity_score:.2f}")
                print(f"  Total score: {total_score:.2f}")
            
            # Optimize playlist
            selected_tracks = self.optimize_playlist(candidate_tracks, playlist_size)
            
            if not selected_tracks:
                raise Exception("No tracks selected during optimization")
            
            print(f"\nSelected {len(selected_tracks)} tracks")
            
            # Create new playlist
            user_id = self.sp.current_user()['id']
            playlist = self.sp.user_playlist_create(
                user_id,
                name=f"TasteTuner Optimized Playlist",
                description="Automatically generated playlist optimized for your taste using artist relationships"
            )
            
            # Add tracks to playlist
            self.sp.playlist_add_items(playlist['id'], selected_tracks)
            
            print(f"\nCreated playlist: https://open.spotify.com/playlist/{playlist['id']}")
            return playlist['id']
            
        except Exception as e:
            print(f"Error creating playlist: {str(e)}")
            raise

def main():
    try:
        # Initialize TasteTuner
        tuner = TasteTuner()
        
        # Create an optimized playlist
        playlist_id = tuner.create_optimized_playlist()
        print(f"Created optimized playlist: https://open.spotify.com/playlist/{playlist_id}")
    except Exception as e:
        print(f"Error in main: {str(e)}")
        raise

if __name__ == "__main__":
    main() 