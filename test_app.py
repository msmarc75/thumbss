import unittest
from unittest.mock import patch, MagicMock
from app import app, JOBS

class TestWebApp(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        JOBS.clear()

    def test_index_route(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Generateur de Miniatures YouTube', response.data.replace(b'\xc3\xa9', b'e'))

    @patch('app.YoutubeOptimizer')
    def test_generate_route(self, MockOptimizer):
        # We don't need to check the thread execution fully, just that it spawns a job
        # and returns the progress page.
        response = self.app.post('/generate', data={'titles': 'Test Video'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'checkStatus', response.data) # Check if JS polling is there
        
        # Check if job was created
        self.assertEqual(len(JOBS), 1)
        job_id = list(JOBS.keys())[0]
        self.assertEqual(JOBS[job_id]['total'], 1)

    @patch('app.fetch_channel_videos')
    def test_fetch_videos_route(self, mock_fetch):
        mock_fetch.return_value = [{'title': 'Vid 1', 'url': 'http://vid1'}]
        response = self.app.post('/fetch_videos', data={'channel_url': 'http://channel'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Vid 1', response.data)
        mock_fetch.assert_called_with('http://channel')

    @patch('app.YoutubeOptimizer')
    def test_generate_selection_route(self, MockOptimizer):
        response = self.app.post('/generate_selection', data={'selected_titles': ['Vid 1', 'Vid 2']})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'checkStatus', response.data)
        
        self.assertEqual(len(JOBS), 1)
        job_id = list(JOBS.keys())[0]
        self.assertEqual(JOBS[job_id]['total'], 2)

    def test_status_route(self):
        job_id = "test-job"
        JOBS[job_id] = {'status': 'processing', 'current': 1, 'total': 2}
        response = self.app.get(f'/status/{job_id}')
        self.assertEqual(response.json['status'], 'processing')

    def test_results_route(self):
        job_id = "test-job-done"
        JOBS[job_id] = {'status': 'completed', 'results': [{'title': 'A', 'thumbnail': 'a.jpg'}]}
        response = self.app.get(f'/results/{job_id}')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'a.jpg', response.data)

if __name__ == '__main__':
    unittest.main()
