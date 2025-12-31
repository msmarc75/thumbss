import unittest
from unittest.mock import MagicMock, patch
import os
import base64
from openai import AuthenticationError
from youtube_optimizer import YoutubeOptimizer

class TestYoutubeOptimizer(unittest.TestCase):

    @patch('youtube_optimizer.OpenAI')
    def setUp(self, MockOpenAI):
        self.mock_client = MockOpenAI.return_value
        self.optimizer = YoutubeOptimizer(api_key="fake-key")

    @patch('youtube_optimizer.Image')
    @patch('youtube_optimizer.requests.get')
    def test_generate_thumbnail_crop_and_compress(self, mock_get, mock_image):
        # Setup mock image generation response with URL
        mock_response = MagicMock()
        mock_response.data[0].url = "http://fake-url.com/image.png"
        self.mock_client.images.generate.return_value = mock_response
        mock_get.return_value.content = b"fake-image-data-url"

        # Setup mock PIL Image
        mock_img_instance = MagicMock()
        mock_img_instance.mode = "RGB"
        # Simulate a 1536x1024 image (3:2 ratio)
        mock_img_instance.size = (1536, 1024)
        
        mock_image.open.return_value = mock_img_instance
        mock_img_instance.convert.return_value = mock_img_instance
        
        # When crop is called, return a new mock with 16:9 dimensions (just for simulation)
        mock_cropped_img = MagicMock()
        mock_cropped_img.size = (1536, 864) # 16:9
        mock_img_instance.crop.return_value = mock_cropped_img

        # Mock open
        with patch("builtins.open", unittest.mock.mock_open()) as mock_file:
            path = self.optimizer.generate_thumbnail("Catchy Title", "test_thumb.jpg")
            
            self.assertEqual(path, "test_thumb.jpg")
            
            # Check PIL usage
            mock_image.open.assert_called()
            
            # Verify Crop logic was triggered (because 1536/1024 != 16/9)
            mock_img_instance.crop.assert_called()
            
            # Calculate expected crop coordinates
            # Target height = 1536 / (16/9) = 864
            # Top = (1024 - 864) // 2 = 80
            # Bottom = 80 + 864 = 944
            mock_img_instance.crop.assert_called_with((0, 80, 1536, 944))
            
            # Verify save is called on the CROPPED image
            mock_cropped_img.save.assert_called() 
            
            mock_file.assert_called_with("test_thumb.jpg", "wb")

    @patch('youtube_optimizer.YoutubeOptimizer.generate_thumbnail')
    def test_process_videos_default_dir(self, mock_gen_thumb):
        # Mock generate_thumbnail to return the path it was called with
        def side_effect(title, path):
            return path
        mock_gen_thumb.side_effect = side_effect
        
        titles = ["Video 1"]
        with patch("os.makedirs") as mock_makedirs:
            results = self.optimizer.process_videos(titles)
            self.assertEqual(len(results), 1)
            
            # Verify the result contains a path in the thumbnails directory
            self.assertTrue(results[0]['thumbnail'].startswith("thumbnails/"))
            self.assertTrue(results[0]['thumbnail'].endswith(".jpg"))

    @patch('youtube_optimizer.YoutubeOptimizer.generate_thumbnail')
    def test_process_videos_custom_dir(self, mock_gen_thumb):
        # Mock generate_thumbnail to return the path it was called with
        def side_effect(title, path):
            return path
        mock_gen_thumb.side_effect = side_effect

        titles = ["Video 1"]
        with patch("os.makedirs") as mock_makedirs:
            results = self.optimizer.process_videos(titles, output_dir="custom_dir")
            
            mock_makedirs.assert_called_with("custom_dir")
            
            # Verify the result contains a path in the custom directory
            self.assertTrue(results[0]['thumbnail'].startswith("custom_dir/"))
            self.assertTrue(results[0]['thumbnail'].endswith(".jpg"))

    def test_process_videos_auth_error(self):
        # Test that AuthenticationError stops the loop
        self.mock_client.images.generate.side_effect = AuthenticationError("Auth failed", response=MagicMock(), body=None)
        
        titles = ["Video 1", "Video 2"]
        
        with patch("os.makedirs"):
            results = self.optimizer.process_videos(titles)
            self.assertEqual(len(results), 0)
            self.assertEqual(self.mock_client.images.generate.call_count, 1)

if __name__ == '__main__':
    unittest.main()
