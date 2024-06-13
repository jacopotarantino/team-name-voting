from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os
import redis
import json
from authlib.integrations.flask_client import OAuth
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up openai client
openai_client = OpenAI(
  api_key = os.environ.get("OPENAI_API_KEY")
)

# Set up Redis client
uri = os.environ.get("REDIS_URL")
redis_client = redis.from_url(uri, decode_responses=True)

# Create app
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")

# OAuth Setup
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.environ.get("GOOGLE_CLIENT_ID"),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
    access_token_url='https://accounts.google.com/o/oauth2/token',
    access_token_params=None,
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params=None,
    client_kwargs={'scope': 'openid email profile'},
)

def generate_team_name_suggestions():
    response = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "user",
                "content": "Generate 3 creative and funny team names, each being a 2-8 word (preferably 3-5 words) pun related to this last week's news."
            }
        ]
    )

    suggestions = response.choices[0].message.content.strip().split('\n')
    return [suggestion.strip() for suggestion in suggestions if suggestion.strip()]

@app.route('/')
def index():
    suggestions = generate_team_name_suggestions()
    user = session.get('user')
    return render_template('index.html', user=user, suggestions=suggestions)

@app.route('/login')
def login():
    redirect_uri = url_for('authorize', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/authorize')
def authorize():
    token = google.authorize_access_token()
    resp = google.get('userinfo')
    user_info = resp.json()
    session['user'] = user_info
    first_name = user_info['given_name']
    if not redis_client.exists(f'user_votes:{first_name}'):
        redis_client.set(f'user_votes:{first_name}', json.dumps([]))
    return redirect(url_for('vote'))

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

@app.route('/vote', methods=['GET', 'POST'])
def vote():
    user = session.get('user')
    if not user:
        return redirect(url_for('index'))

    first_name = user['given_name']
    user_votes = json.loads(redis_client.get(f'user_votes:{first_name}'))

    if request.method == 'POST':
        if 'team_name' in request.form:
            team_name = request.form['team_name']
            if not redis_client.exists(f'team_name:{team_name}'):
                redis_client.set(f'team_name:{team_name}', 0)

        else:
            team_name = request.form['vote']
            if len(user_votes) < 3:
                redis_client.incr(f'team_name:{team_name}')
                user_votes.append(team_name)
                redis_client.set(f'user_votes:{first_name}', json.dumps(user_votes))

    def sort_second(val):
        return val[1]

    team_names = [(key.split(':')[1], redis_client.get(key)) for key in redis_client.keys('team_name:*')]
    team_names.sort(key=sort_second, reverse=True)

    return render_template('vote.html', team_names=team_names, user_votes=user_votes)

if __name__ == '__main__':
    app.run(debug=True)
