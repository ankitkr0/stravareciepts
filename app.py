# app.py
from flask import Flask, render_template, redirect, url_for, session, request
from stravalib.client import Client
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import pandas as pd

app = Flask(__name__)
app.secret_key = os.urandom(24)
load_dotenv()

CLIENT_ID = int(os.getenv('STRAVA_CLIENT_ID'))
CLIENT_SECRET = os.getenv('STRAVA_CLIENT_SECRET')
REDIRECT_URI = os.getenv('REDIRECT_URI', 'http://127.0.0.1:5000/authorized')

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/authorize')
def authorize():
    client = Client()
    url = client.authorization_url(
        client_id=CLIENT_ID,
        redirect_uri=REDIRECT_URI,
        scope=['read', 'activity:read_all', 'profile:read_all'],
        approval_prompt='auto'
    )
    return redirect(url)

@app.route('/authorized')
def authorized():
    error = request.args.get('error')
    if error:
        return f'Error: {error}'
        
    code = request.args.get('code')
    client = Client()
    
    try:
        token_response = client.exchange_code_for_token(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            code=code
        )
        
        print("Token response:", token_response)
        
        session['access_token'] = token_response['access_token']
        session['refresh_token'] = token_response['refresh_token'] 
        session['expires_at'] = token_response['expires_at']
        
        return redirect(url_for('generate_receipt'))
        
    except Exception as e:
        print("Authorization error:", str(e))
        return f"Authorization failed: {str(e)}", 400

@app.route('/receipt')
def generate_receipt():
    if 'access_token' not in session:
        return redirect(url_for('authorize'))
    
    try:
        client = Client(access_token=session['access_token'])
        
        # Get athlete info
        athlete = client.get_athlete()
        
        # Calculate date range (last 365 days)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        
        # Get activities
        activities = list(client.get_activities(after=start_date))
        
        if not activities:
            return render_template('receipt.html', 
                                error="No activities found in the past year!")

        # Process activities
        stats = {
            'total_activities': len(activities),
            'total_distance': sum(a.distance.num for a in activities if hasattr(a, 'distance')),
            'total_time': sum(a.moving_time.total_seconds() for a in activities if hasattr(a, 'moving_time')),
            'total_elevation': sum(a.total_elevation_gain.num for a in activities if hasattr(a, 'total_elevation_gain')),
            'activity_types': {},
            'kudos_received': sum(a.kudos_count for a in activities if hasattr(a, 'kudos_count')),
            'achievements': sum(a.achievement_count for a in activities if hasattr(a, 'achievement_count')),
            'longest_activity': max((a.distance.num for a in activities if hasattr(a, 'distance')), default=0),
            'highest_elevation': max((a.total_elevation_gain.num for a in activities if hasattr(a, 'total_elevation_gain')), default=0)
        }

        # Count activity types
        for activity in activities:
            activity_type = activity.type
            stats['activity_types'][activity_type] = stats['activity_types'].get(activity_type, 0) + 1

        # Calculate averages
        stats['avg_distance'] = stats['total_distance'] / stats['total_activities']
        stats['avg_time'] = stats['total_time'] / stats['total_activities']
        
        # Format time
        stats['total_time_formatted'] = str(timedelta(seconds=int(stats['total_time'])))
        stats['avg_time_formatted'] = str(timedelta(seconds=int(stats['avg_time'])))

        # Get most active day
        activity_dates = pd.Series([a.start_date.strftime('%A') for a in activities])
        stats['most_active_day'] = activity_dates.mode().iloc[0]

        return render_template('receipt.html',
                             athlete=athlete,
                             stats=stats,
                             start_date=start_date,
                             end_date=end_date)

    except Exception as e:
        return f"An error occurred: {str(e)}", 500

def refresh_token():
    if 'refresh_token' not in session:
        return False
        
    client = Client()
    
    try:
        token_response = client.refresh_access_token(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET, 
            refresh_token=session['refresh_token']
        )
        
        session['access_token'] = token_response['access_token']
        session['refresh_token'] = token_response['refresh_token']
        session['expires_at'] = token_response['expires_at']
        
        return True
        
    except Exception:
        return False

if __name__ == '__main__':
    app.run(debug=True)