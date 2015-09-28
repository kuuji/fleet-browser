import os
import sys
import unittest
import pyotp
from flask import session

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import app as app_module

class AppTestCase(unittest.TestCase):

    def setUp(self):
        app_module.app.config['TESTING'] = True
        self.app = app_module.app.test_client()

    def tearDown(self):
        pass

    def test_ping(self):
            rv = self.app.get('/ping')
            assert rv.status_code == 200
            assert rv.data == 'OK'

    def test_login_without_TOTP(self):
        # Try to login with wrong password
        rv = self.app.post('/login', data={'username': 'admin', 'password': 'ola'})
        assert 'Invalid Credentials. Please try again.' in rv.data

        # Try to login with correct credentials
        rv = self.app.post('/login', data={'username': 'admin', 'password': 'admin'})
        assert rv.status_code == 302

    def test_login_with_TOTP(self):
        # Set TOTP by reimporting the module
        totp = pyotp.TOTP('AAAABBBBCCCCDDDD')
        app_module.TOTP = totp

        # Try to pass through the TOTP page setting a wrong TOTP code
        rv = self.app.post('/totp', data={'totp-token': '123456'})
        assert 'Wrong TOTP token' in rv.data

        # Try to pass through the TOTP page setting a wrong TOTP format
        rv = self.app.post('/totp', data={'totp-token': 'abcdef'})
        assert 'The token is a 6 digit number' in rv.data

        # Try to pass through the TOTP page setting a valid TOTP code
        # (should redirect to /login as we haven't logged)
        rv = self.app.post('/totp', data={'totp-token': totp.now()},
                           follow_redirects=True)
        assert 'Please enter you username' in rv.data

        # Try to login with wrong password
        rv = self.app.post('/login', data={'username': 'admin', 'password': 'ola'})
        assert 'Invalid Credentials. Please try again.' in rv.data

        # Try to login with correct credentials (should redirect to /totp)
        rv = self.app.post('/login', data={'username': 'admin', 'password': 'admin'},
                           follow_redirects=True)
        assert 'Please enter the authentication code' in rv.data

        # Try to pass through the TOTP page setting a valid TOTP code
        # (should redirect to /state as we are logged now)
        rv = self.app.post('/totp', data={'totp-token': totp.now()},
                           follow_redirects=True)
        assert '(&#39;Connection aborted.&#39;, error(113, &#39;No route to host&#39;))' in rv.data

        # Unset TOTP
        app_module.TOTP = None

    def test_logout(self):
        # First we login
        rv = self.app.post('/login', data={'username': 'admin', 'password': 'admin'})

        # We can access /state, but it'll error with no Fleet connection
        rv = self.app.get('/state', follow_redirects=True)
        assert '(&#39;Connection aborted.&#39;, error(113, &#39;No route to host&#39;))' in rv.data

        # Now we logout
        rv = self.app.get('/logout')

        # We cannot access /state
        rv = self.app.get('/state', follow_redirects=True)
        assert 'Please enter you username' in rv.data

if __name__ == '__main__':
    unittest.main()
