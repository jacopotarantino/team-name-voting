from flask import Flask, render_template, request, redirect, url_for, session
from pymongo import MongoClient
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "ozempicisruiningeverything")

# Set up MongoDB client
uri = os.environ.get("DATABASE_URL")
client = MongoClient(uri)
db = client['TeamNames0']
team_names_collection = db['team_names']
user_votes_collection = db['user_votes']

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        first_name = request.form['first_name']
        session['first_name'] = first_name
        if user_votes_collection.find_one({'first_name': first_name}) is None:
            user_votes_collection.insert_one({'first_name': first_name, 'votes': []})
        return redirect(url_for('vote'))

    return render_template('index.html')

@app.route('/vote', methods=['GET', 'POST'])
def vote():
    if 'first_name' not in session:
        return redirect(url_for('index'))
    
    first_name = session['first_name']
    user_data = user_votes_collection.find_one({'first_name': first_name})
    user_votes = user_data['votes'] if user_data else []
    
    if request.method == 'POST':
        if 'team_name' in request.form:
            team_name = request.form['team_name']
            if team_names_collection.find_one({'name': team_name}) is None:
                team_names_collection.insert_one({'name': team_name, 'score': 0})
        
        else:
            team_name = request.form['vote']
            if len(user_votes) < 3 and team_name not in user_votes:
                team_names_collection.update_one({'name': team_name}, {'$inc': {'score': 1}})
                user_votes_collection.update_one({'first_name': first_name}, {'$push': {'votes': team_name}})
                user_votes.append(team_name)
    
    team_names = list(team_names_collection.find())
    
    return render_template('vote.html', team_names=team_names, user_votes=user_votes)

if __name__ == '__main__':
    app.run(debug=True)

