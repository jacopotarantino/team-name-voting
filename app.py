from flask import Flask, render_template, request, redirect, url_for, session
import os
import redis
import json
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

@app.route('/', methods=['GET', 'POST'])
def index():
    def generate_team_name_suggestions():
        completion = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "user",
                    "content": "Generate 3 creative and funny team names, each being a 2-8 word (preferably 3-5 words) pun related to this last week's news.",
                }
            ],
        )

        suggestions = completion.choices[0].message.content.strip().split('\n')
        return [suggestion.strip() for suggestion in suggestions if suggestion.strip()]

    if request.method == 'POST':
        first_name = request.form['first_name']
        session['first_name'] = first_name
        if not redis_client.exists(f'user_votes:{first_name}'):
            redis_client.set(f'user_votes:{first_name}', json.dumps([]))
        return redirect(url_for('vote'))

    suggestions = generate_team_name_suggestions()
    return render_template('index.html', suggestions=suggestions)

@app.route('/vote', methods=['GET', 'POST'])
def vote():
    if 'first_name' not in session:
        return redirect(url_for('index'))
    
    first_name = session['first_name']
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

