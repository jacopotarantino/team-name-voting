from flask import Flask, render_template, request, redirect, url_for, session
import os
import redis
import json

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "ozempicisruiningeverything")

# Set up Redis client
uri = os.environ.get("REDIS_URL")
redis_client = redis.from_url(uri, decode_responses=True)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        first_name = request.form['first_name']
        session['first_name'] = first_name
        if not redis_client.exists(f'user_votes:{first_name}'):
            redis_client.set(f'user_votes:{first_name}', json.dumps([]))
        return redirect(url_for('vote'))

    return render_template('index.html')

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
            if len(user_votes) < 3 and team_name not in user_votes:
                redis_client.incr(f'team_name:{team_name}')
                user_votes.append(team_name)
                redis_client.set(f'user_votes:{first_name}', json.dumps(user_votes))

    team_names = [(key.split(':')[1], redis_client.get(key)) for key in redis_client.keys('team_name:*')]

    return render_template('vote.html', team_names=team_names, user_votes=user_votes)

if __name__ == '__main__':
    app.run(debug=True)

