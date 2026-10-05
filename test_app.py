import unittest
import json
import app

class ExposysAppTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.app.test_client()

    def test_homepage(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Exposys Data Labs', response.data)

    def test_api_candidates(self):
        response = self.client.get('/api/candidates?your_name=Manoj+Gowda&roll_number=12345')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['total_candidates'], 9)
        self.assertEqual(data['selected_candidates_count'], 6)
        self.assertEqual(data['highest_score'], 99)

    def test_api_top6(self):
        response = self.client.get('/api/top6?your_name=Manoj+Gowda&roll_number=12345')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        top6 = data['top6']
        self.assertEqual(len(top6), 6)
        
        # Check ranks 1 through 6
        expected_names = ['Ksihore', 'Mahindar', 'Prashanth', 'Exposys', 'Vishnu', 'Theertha']
        actual_names = [c['name'] for c in top6]
        self.assertEqual(actual_names, expected_names)

        # Check phone cleaning (+91 prefix)
        for cand in top6:
            self.assertTrue(cand['phone'].startswith('91'))
            self.assertEqual(len(cand['phone']), 12)
            self.assertIn('https://wa.me/', cand['whatsapp_url'])

    def test_api_candidate_detail(self):
        response = self.client.get('/api/candidate/8?your_name=Manoj+Gowda&roll_number=12345')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['candidate']['name'], 'Ksihore')

    def test_candidate_not_found(self):
        response = self.client.get('/api/candidate/999')
        self.assertEqual(response.status_code, 404)

    def test_batch_send_status_endpoint(self):
        response = self.client.get('/api/batch_send_status')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertIn('batch_state', data)
        self.assertIn('status', data['batch_state'])

    def test_cancel_batch_send_when_idle(self):
        response = self.client.post('/api/cancel_batch_send')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('success', data)

    def test_api_send_whatsapp_all_auto(self):
        from unittest.mock import patch
        with patch('threading.Thread.start') as mock_thread_start:
            response = self.client.post('/api/send_whatsapp_all_auto', 
                                        data=json.dumps({'your_name': 'Manoj Gowda', 'roll_number': '12345'}),
                                        content_type='application/json')
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertTrue(data['success'])
            self.assertEqual(data['total_candidates'], 6)
            self.assertEqual(len(data['candidates']), 6)
            mock_thread_start.assert_called_once()

if __name__ == '__main__':
    unittest.main()

