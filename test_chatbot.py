"""
Simple test suite for 362AniBot - Core functionality tests
Tests the main chatbot features in a single file
"""

import unittest
import json
import sys
import os
from unittest.mock import patch, Mock

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

import app


class TestAniBot(unittest.TestCase):
    """Test core chatbot functionality"""

    def setUp(self):
        """Set up test environment"""
        app.app.config['TESTING'] = True
        self.client = app.app.test_client()

    @patch('app.requests.post')
    def test_anilist_api_success(self, mock_post):
        """Test AniList API returns anime data"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "Media": {
                    "id": 101922,
                    "title": {"english": "Test Anime"},
                    "genres": ["Action"],
                    "averageScore": 85
                }
            }
        }
        mock_post.return_value = mock_response
        
        results = app.fetch_anilist_recommendations(count=1)
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title']['english'], "Test Anime")

    @patch('app.requests.post')
    def test_anilist_api_failure(self, mock_post):
        """Test AniList API handles errors gracefully"""
        import requests
        mock_post.side_effect = requests.RequestException("Network error")
        
        results = app.fetch_anilist_recommendations(count=1)
        
        self.assertEqual(results, [])

    def test_recommendations_to_prompt(self):
        """Test converting anime data to chat prompt"""
        anime_data = [{
            "title": {"english": "Test Anime"},
            "genres": ["Action", "Drama"],
            "averageScore": 85
        }]
        
        prompt = app.recommendations_to_prompt(anime_data)
        
        self.assertIn("Test Anime", prompt)
        self.assertIn("Action, Drama", prompt)
        self.assertIn("Score: 85", prompt)

    def test_chat_endpoint_missing_messages(self):
        """Test chat endpoint requires messages"""
        response = self.client.post('/api/chat', json={})
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("messages", data["error"])

    def test_chat_endpoint_empty_messages(self):
        """Test chat endpoint rejects empty messages"""
        response = self.client.post('/api/chat', json={"messages": []})
        
        self.assertEqual(response.status_code, 400)

    @patch('app._client')
    def test_chat_endpoint_no_openai_client(self, mock_client):
        """Test chat endpoint when OpenAI not configured"""
        app._client = None
        
        response = self.client.post('/api/chat', 
                                  json={"messages": [{"role": "user", "content": "test"}]})
        
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.data)
        self.assertIn("OpenAI client not initialized", data["error"])

    @patch('app._client')
    @patch('app.fetch_anilist_recommendations')
    def test_chat_endpoint_success(self, mock_fetch, mock_client):
        """Test successful chat response"""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Great anime choice!"
        mock_response.usage = None
        mock_client.chat.completions.create.return_value = mock_response
        
        # Mock AniList response
        mock_fetch.return_value = [{"title": {"english": "Test Anime"}}]
        
        response = self.client.post('/api/chat',
                                  json={"messages": [{"role": "user", "content": "recommend anime"}]})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["reply"], "Great anime choice!")
        self.assertIn("metadata", data)

    @patch('app.fetch_anilist_recommendations')
    def test_recommendation_endpoint_success(self, mock_fetch):
        """Test recommendation endpoint returns anime"""
        mock_fetch.return_value = [{"id": 1, "title": {"english": "Test Anime"}}]
        
        response = self.client.get('/api/recommendation?count=1')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], 1)

    @patch('app.fetch_anilist_recommendations')
    def test_recommendation_endpoint_no_results(self, mock_fetch):
        """Test recommendation endpoint when no anime found"""
        mock_fetch.return_value = []
        
        response = self.client.get('/api/recommendation')
        
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.data)
        self.assertIn("Could not fetch anime", data["error"])

    def test_root_endpoint_serves_frontend(self):
        """Test that root endpoint works"""
        response = self.client.get('/')
        # Should return 200 or 404 depending on if index.html exists
        self.assertIn(response.status_code, [200, 404])


if __name__ == '__main__':
    print("🤖 Running 362AniBot Tests")
    print("=" * 40)
    
    # Run tests
    unittest.main(verbosity=2, exit=False)
    
    print("\n" + "=" * 40)
    print("✅ Test run complete!")