# app.py
from flask import Flask, render_template, redirect, url_for, session, request
from stravalib.client import Client
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import random
from dataclasses import dataclass
from typing import List

app = Flask(__name__)
app.secret_key = os.urandom(24)
load_dotenv()

CLIENT_ID = os.getenv('STRAVA_CLIENT_ID')
CLIENT_SECRET = os.getenv('STRAVA_CLIENT_SECRET')
REDIRECT_URI = 'https://stravaexperiment.vercel.app/authorized'

@dataclass
class ReceiptItem:
    name: str
    price: str

@dataclass
class Receipt:
    receipt_no: str
    date: str
    athlete_name: str
    cashier: str
    receipt_items: List[ReceiptItem]
    footer_messages: List[str]

def calculate_activity_stats(activities):
    """Calculate various stats from activities for the receipt."""
    stats = {
        'total_distance': 0,
        'total_time': 0,
        'total_elevation': 0,
        'activities_count': len(activities),
        'kudos_count': 0,
        'activity_types': {}
    }
    
    for activity in activities:
        # Basic stats
        stats['total_distance'] += float(activity.distance.num)
        stats['total_time'] += float(activity.moving_time.total_seconds())
        stats['total_elevation'] += float(activity.total_elevation_gain)
        stats['kudos_count'] += activity.kudos_count
        
        # Track activity types
        activity_type = activity.type
        stats['activity_types'][activity_type] = stats['activity_types'].get(activity_type, 0) + 1
    
    return stats

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/authorize')
def authorize():
    client = Client()
    url = client.authorization_url(
        client_id=CLIENT_ID,
        redirect_uri=REDIRECT_URI,
        scope=['read_all', 'profile:read_all', 'activity:read_all']
    )
    return redirect(url)

@app.route('/authorized')
def authorized():
    code = request.args.get('code')
    client = Client()
    token_response = client.exchange_code_for_token(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        code=code
    )
    session['access_token'] = token_response['access_token']
    return redirect(url_for('generate_receipt'))

@app.route('/receipt')
def generate_receipt():
    if 'access_token' not in session:
        return redirect(url_for('authorize'))
    
    client = Client(access_token=session['access_token'])
    athlete = client.get_athlete()
    
    # Get activities from last 30 days
    after = datetime.now() - timedelta(days=30)
    activities = list(client.get_activities(after=after))
    
    stats = calculate_activity_stats(activities)
    
    receipt_items = [
        ReceiptItem(
            name="TOTAL DISTANCE",
            price=f"{stats['total_distance'] / 1000:.1f} KM"
        ),
        ReceiptItem(
            name=f"ACTIVITIES ({', '.join(f'{v}x {k}' for k, v in stats['activity_types'].items())})",
            price=str(stats['activities_count'])
        ),
        ReceiptItem(
            name="ELEVATION GAINED",
            price=f"{stats['total_elevation']:.0f}M"
        ),
        ReceiptItem(
            name="KUDOS COLLECTED",
            price=str(stats['kudos_count'])
        ),
        ReceiptItem(
            name="TIME INVESTED",
            price=f"{stats['total_time'] / 3600:.1f}HRS"
        )
    ]
    
    receipt = Receipt(
        receipt_no=f"STR-{random.randint(10000, 99999)}",
        date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        athlete_name=athlete.firstname,
        cashier=f"STRAVA BOT #{random.randint(1, 999)}",
        receipt_items=receipt_items,
        footer_messages=[
            "NO REFUNDS ON BURNED CALORIES",
            "THANKS FOR SWEATING WITH US",
            "PAIN IS TEMPORARY, STRAVA IS FOREVER",
            f"YOU'RE FASTER THAN {random.randint(50, 95)}% OF CUSTOMERS"
        ]
    )
    
    return render_template('receipt.html', receipt=receipt)

if __name__ == '__main__':
    app.run()