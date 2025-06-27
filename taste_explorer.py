import os
import time
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
import numpy as np
from collections import defaultdict
from tqdm import tqdm

class TasteExplorer:
    def __init__(self):
        load_dotenv()
        
        # Authentication 
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
            
        # Initialize graph data structures
        self.artist_connections = defaultdict(set)  # artist -> related artists
        self.artist_genres = defaultdict(set)      # artist -> genres
        self.genre_artists = defaultdict(set)      # genre -> artists
        self.artist_tracks = defaultdict(set)      # artist -> tracks
        self.track_features = {}                   # track -> features
        
    def build_music_graph(self):
        """Build a graph of musical relationships"""
        print("\nBuilding music relationship graph...")
        
        # Get user's top artists and tracks
        top_artists = []
        top_tracks = []
        
        for time_range in ['short_term', 'medium_term', 'long_term']:
            try:
                artists = self.sp.current_user_top_artists(limit=20, time_range=time_range)
                tracks = self.sp.current_user_top_tracks(limit=20, time_range=time_range)
                
                top_artists.extend(artists['items'])
                top_tracks.extend(tracks['items'])
            except Exception as e:
                print(f"Error getting top items for {time_range}: {str(e)}")
                continue
        
        # Add user's saved tracks
        try:
            saved = self.sp.current_user_saved_tracks(limit=50)
            top_tracks.extend(saved['items'])
        except Exception as e:
            print(f"Error getting saved tracks: {str(e)}")
        
        # Process artists
        print("\nProcessing artists and their relationships...")
        for artist in tqdm(top_artists):
            artist_id = artist['id']
            
            # Add genres
            for genre in artist['genres']:
                self.artist_genres[artist_id].add(genre)
                self.genre_artists[genre].add(artist_id)
            
            # Get top tracks
            try:
                time.sleep(0.1)  # Rate limiting
                top_tracks = self.sp.artist_top_tracks(artist_id)
                for track in top_tracks['tracks']:
                    self.artist_tracks[artist_id].add(track['id'])
                    self.track_features[track['id']] = {
                        'name': track['name'],
                        'popularity': track['popularity'],
                        'preview_url': track['preview_url'],
                        'artist_name': track['artists'][0]['name'],
                        'artist_id': track['artists'][0]['id']
                    }
            except Exception as e:
                print(f"Error getting top tracks for {artist['name']}: {str(e)}")
                continue
            
            # Get related artists
            try:
                time.sleep(0.1)  # Rate limiting
                related = self.sp.artist_related_artists(artist_id)
                for related_artist in related['artists']:
                    self.artist_connections[artist_id].add(related_artist['id'])
                    
                    # Add genres for related artists
                    for genre in related_artist['genres']:
                        self.artist_genres[related_artist['id']].add(genre)
                        self.genre_artists[genre].add(related_artist['id'])
            except Exception as e:
                print(f"Error getting related artists for {artist['name']}: {str(e)}")
                continue
    
    def calculate_discovery_scores(self):
        """Calculate discovery scores for all tracks"""
        print("\nCalculating discovery scores...")
        
        discovery_scores = {}
        user_genres = set()
        
        # Collect user's preferred genres
        for artist_id in self.artist_genres:
            user_genres.update(self.artist_genres[artist_id])
        
        # Calculate scores for each track
        for track_id, track_info in self.track_features.items():
            artist_id = track_info['artist_id']
            
            # Genre match score
            artist_genres = self.artist_genres[artist_id]
            genre_score = len(artist_genres & user_genres) / max(len(user_genres), 1)
            
            # Artist connection score (how well connected to user's taste)
            connection_score = len(self.artist_connections[artist_id]) / 20.0  # Normalize by max connections
            
            # Popularity score (favor less popular tracks for discovery)
            popularity_score = 1.0 - (track_info['popularity'] / 100.0)
            
            # Combined score with weights
            discovery_scores[track_id] = {
                'score': 0.4 * genre_score + 0.3 * connection_score + 0.3 * popularity_score,
                'track_info': track_info
            }
        
        return discovery_scores
    
    def create_discovery_playlist(self, playlist_size=20):
        """Create a playlist of music discoveries"""
        try:
            # Build the music graph
            self.build_music_graph()
            
            # Calculate discovery scores
            discovery_scores = self.calculate_discovery_scores()
            
            # Sort tracks by score
            sorted_tracks = sorted(
                discovery_scores.items(),
                key=lambda x: x[1]['score'],
                reverse=True
            )
            
            # Select top tracks
            selected_tracks = sorted_tracks[:playlist_size]
            
            # Create playlist
            user_id = self.sp.current_user()['id']
            playlist = self.sp.user_playlist_create(
                user_id,
                name="TasteExplorer Discoveries",
                description="New music discoveries based on your taste graph"
            )
            
            # Add tracks to playlist
            track_ids = [track_id for track_id, _ in selected_tracks]
            self.sp.playlist_add_items(playlist['id'], track_ids)
            
            print(f"\nCreated discovery playlist: https://open.spotify.com/playlist/{playlist['id']}")
            
            # Print selected tracks and their scores
            print("\nSelected tracks:")
            for track_id, info in selected_tracks:
                track_info = info['track_info']
                print(f"{track_info['name']} by {track_info['artist_name']} (Score: {info['score']:.3f})")
            
            return playlist['id']
            
        except Exception as e:
            print(f"Error creating discovery playlist: {str(e)}")
            raise

def main():
    explorer = TasteExplorer()
    explorer.create_discovery_playlist()

if __name__ == "__main__":
    main() 