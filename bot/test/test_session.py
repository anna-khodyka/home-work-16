import sys
import os
from flask import session as flask_session


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))
sys.path.append('../')

from main import init_app
from init_bp import before_request



def test_request_context(app, client):

    app.before_request_funcs[None] = [before_request]
    with app.test_request_context():
        response = client.post('/DB_select', data={'db': 'mongodb'})
        assert response.status_code == 302
        # Did we choos the DB?
        assert response.headers['Location'] == 'http://localhost/login/login', 
        # 'db' should be in session!
        assert 'db' in flask_session
        #It's not. Is there anything else in session?
        assert len(flask_session) != 0



def test_session_context(app, client):
    with app.app_context():
        #We haven't scoose the db yet, so 'db' couldn't be in flask_session
        assert 'db' not in flask_session
        
        response = client.post('/DB_select', data={'db': 'mongodb'})
        #Now we have choosen DBE, so 'db' should be in flask_session
        assert 'db' in app.flask_session

