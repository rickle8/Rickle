from flask import Flask, render_template, request, jsonify, session
import json
import os
from datetime import datetime
import subprocess

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Ensure Flask app dynamically loads updated data
LEAGUE_HISTORY_FILE = os.path.join(os.path.dirname(__file__), "league_history.json")
CHAT_LOG_FILE = os.path.join(os.path.dirname(__file__), "chat_log.json")

# Ensure chat log file exists
if not os.path.exists(CHAT_LOG_FILE):
    with open(CHAT_LOG_FILE, "w") as f:
        json.dump([], f)

# Function to load league data dynamically
def load_league_data():
    try:
        with open(LEAGUE_HISTORY_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print("Error: league_history.json not found. Run build_json.py first!")
        return {}
    except json.JSONDecodeError:
        print("Error: league_history.json is corrupted. Rebuild it with build_json.py!")
        return {}

# Function to update league data by running the scraper
def update_league_data():
    try:
        print("Running league_history_scraper.py...")
        subprocess.run(["python3", "league_history_scraper.py"], check=True)
        global league_data
        league_data = load_league_data()
        print("League data updated successfully.")
    except Exception as e:
        print(f"Error updating league data: {e}")

# Ensure Flask app dynamically loads updated data
league_data = load_league_data()

def calculate_overall_records():
    """Calculates total wins, losses, and ties for each owner across all years."""
    overall_records = {}
    for year, data in league_data.items():
        for team in data.get("teams", []):
            owner = team.get("owner", "Unknown")
            if owner not in overall_records:
                overall_records[owner] = {"wins": 0, "losses": 0, "ties": 0}
            overall_records[owner]["wins"] += team.get("wins", 0)
            overall_records[owner]["losses"] += team.get("losses", 0)
            overall_records[owner]["ties"] += team.get("ties", 0)
    return overall_records

def calculate_historical_head_to_head():
    """Calculates historical head-to-head records across all years."""
    all_owners = set()
    for year, data in league_data.items():
        for team in data.get("teams", []):
            all_owners.add(team.get("owner", "Unknown"))

    head_to_head = {owner: {opp: {"wins": 0, "losses": 0, "ties": 0} for opp in all_owners if opp != owner} for owner in all_owners}

    for year, data in league_data.items():
        for owner, matchups in data.get("head_to_head", {}).items():
            for opponent, record in matchups.items():
                if owner in head_to_head and opponent in head_to_head[owner]:
                    head_to_head[owner][opponent]["wins"] += record.get("wins", 0)
                    head_to_head[owner][opponent]["losses"] += record.get("losses", 0)
                    head_to_head[owner][opponent]["ties"] += record.get("ties", 0)
    return head_to_head

def get_champions():
    """Gets the champion for each year (rank 1 team)."""
    champions = []
    for year in sorted(league_data.keys(), reverse=True):
        for team in league_data[year]['teams']:
            if team['rank'] == 1:
                champions.append({'year': year, 'team': team['name'], 'owner': team['owner']})
                break
    return champions

def get_power_rankings():
    """Calculates power rankings based on win percentage and total points scored."""
    owner_stats = {}

    # Aggregate owner stats (wins, losses, ties, points_for)
    for year, data in league_data.items():
        for team in data.get("teams", []):
            owner = team.get("owner", "Unknown")
            if owner not in owner_stats:
                owner_stats[owner] = {"wins": 0, "losses": 0, "ties": 0, "points_for": 0}
            owner_stats[owner]["wins"] += team.get("wins", 0)
            owner_stats[owner]["losses"] += team.get("losses", 0)
            owner_stats[owner]["ties"] += team.get("ties", 0)
            owner_stats[owner]["points_for"] += team.get("points_for", 0)

    # Combine stats for active and retired Chris Nguyen
    if "Chris Nguyen" in owner_stats and "Chris  Nguyen" in owner_stats:
        owner_stats["Chris Nguyen"]["wins"] += owner_stats["Chris  Nguyen"]["wins"]
        owner_stats["Chris Nguyen"]["losses"] += owner_stats["Chris  Nguyen"]["losses"]
        owner_stats["Chris Nguyen"]["ties"] += owner_stats["Chris  Nguyen"]["ties"]
        owner_stats["Chris Nguyen"]["points_for"] += owner_stats["Chris  Nguyen"]["points_for"]
        del owner_stats["Chris  Nguyen"]

    # Calculate win percentage for each owner
    for owner, stats in owner_stats.items():
        total_games = stats["wins"] + stats["losses"] + stats["ties"]
        stats["win_percentage"] = stats["wins"] / total_games if total_games > 0 else 0

    # Define active owners (owners with teams in the most recent year)
    latest_year = max(league_data.keys(), key=int)
    active_owners = {team["owner"] for team in league_data[latest_year].get("teams", [])}

    # Calculate championship counts
    championship_counts = {}
    for year in league_data:
        for team in league_data[year]["teams"]:
            if team["rank"] == 1:
                owner = team["owner"]
                championship_counts[owner] = championship_counts.get(owner, 0) + 1

    # Active rankings (win percentage only)
    active_rankings = sorted(
        [(owner, stats) for owner, stats in owner_stats.items() if owner in active_owners],
        key=lambda x: x[1]["win_percentage"],
        reverse=True
    )
    active_rankings_data = [
        {
            "rank": i + 1,
            "owner": owner,
            "win_percentage": round(stats["win_percentage"] * 100, 2),
            "championships": championship_counts.get(owner, 0)
        }
        for i, (owner, stats) in enumerate(active_rankings)
    ]

    # Retired rankings (win percentage only)
    retired_rankings = sorted(
        [(owner, stats) for owner, stats in owner_stats.items() if owner not in active_owners],
        key=lambda x: x[1]["win_percentage"],
        reverse=True
    )
    retired_rankings_data = [
        {
            "rank": i + 1,
            "owner": owner,
            "win_percentage": round(stats["win_percentage"] * 100, 2),
            "championships": championship_counts.get(owner, 0)
        }
        for i, (owner, stats) in enumerate(retired_rankings)
    ]

    # Points scored rankings (total points only)
    points_scored_rankings = sorted(
        owner_stats.items(),
        key=lambda x: x[1]["points_for"],
        reverse=True
    )
    points_scored_data = [
        {
            "rank": i + 1,
            "owner": owner,
            "points_for": round(stats["points_for"], 1)
        }
        for i, (owner, stats) in enumerate(points_scored_rankings)
    ]

    return {
        "active": active_rankings_data,
        "retired": retired_rankings_data,
        "points_scored": points_scored_data
    }

def calculate_scoring_records():
    """Calculate scoring records like highest score, lowest score, and biggest blowouts."""
    highest_score = {"team": None, "score": 0, "year": None, "week": None}
    lowest_score = {"team": None, "score": float('inf'), "year": None, "week": None}
    biggest_blowout = {"teams": None, "margin": 0, "year": None, "week": None}

    for year, data in league_data.items():
        for week, matchups in data.get("weekly_scores", {}).items():
            for matchup in matchups:
                home_team = matchup.get("home_team")
                away_team = matchup.get("away_team")
                home_score = matchup.get("home_score", 0)
                away_score = matchup.get("away_score", 0)

                # Check for highest score
                if home_score > highest_score["score"]:
                    highest_score = {"team": home_team, "score": home_score, "year": year, "week": week}
                if away_score > highest_score["score"]:
                    highest_score = {"team": away_team, "score": away_score, "year": year, "week": week}

                # Check for lowest score
                if home_score < lowest_score["score"]:
                    lowest_score = {"team": home_team, "score": home_score, "year": year, "week": week}
                if away_score < lowest_score["score"]:
                    lowest_score = {"team": away_team, "score": away_score, "year": year, "week": week}

                # Check for biggest blowout
                margin = abs(home_score - away_score)
                if margin > biggest_blowout["margin"]:
                    biggest_blowout = {"teams": f"{home_team} vs {away_team}", "margin": margin, "year": year, "week": week}

    return {
        "highest_score": highest_score,
        "lowest_score": lowest_score,
        "biggest_blowout": biggest_blowout
    }

def calculate_highest_scoring_team_all_time():
    """Calculate the highest scoring team of all time."""
    highest_scoring_team = {"team": None, "score": 0, "year": None}

    for year, data in league_data.items():
        for team in data.get("teams", []):
            if team.get("points_for", 0) > highest_scoring_team["score"]:
                highest_scoring_team = {
                    "team": team["name"],
                    "score": team["points_for"],
                    "year": year
                }

    return highest_scoring_team

def calculate_lowest_scoring_team_all_time():
    """Calculate the lowest scoring team of all time."""
    lowest_scoring_team = {"team": None, "score": float('inf'), "year": None}

    for year, data in league_data.items():
        for team in data.get("teams", []):
            if team.get("points_for", 0) < lowest_scoring_team["score"]:
                lowest_scoring_team = {
                    "team": team["name"],
                    "score": team["points_for"],
                    "year": year
                }

    return lowest_scoring_team

# Add highest scoring team of all time to the home route
@app.route('/')
def home():
    champions = get_champions()
    standings_by_year = {}
    for year in league_data.keys():
        teams = sorted(league_data[year].get("teams", []), key=lambda x: x.get("rank", float('inf')))
        standings_by_year[year] = teams

    scoring_records = calculate_scoring_records()
    highest_scoring_team_all_time = calculate_highest_scoring_team_all_time()
    lowest_scoring_team_all_time = calculate_lowest_scoring_team_all_time()

    return render_template("index.html", 
                           years=sorted(league_data.keys(), reverse=True), 
                           champions=champions, 
                           league_data=league_data, 
                           standings_by_year=standings_by_year, 
                           league_history=league_data,
                           scoring_records=scoring_records,
                           highest_scoring_team_all_time=highest_scoring_team_all_time,
                           lowest_scoring_team_all_time=lowest_scoring_team_all_time)

@app.route('/year/<int:year>')
def year_view(year):
    year_data = league_data.get(str(year), {})
    teams = sorted(year_data.get("teams", []), key=lambda x: x.get("rank", float('inf')))
    weekly_scores = year_data.get("weekly_scores", {})
    overall_records = calculate_overall_records()

    # Debugging output
    print(f"DEBUG: Year {year} Teams:", teams)
    print(f"DEBUG: Year {year} Weekly Scores:", weekly_scores)

    # Build weekly summary for each team
    team_weekly_summaries = {}
    for team in teams:
        team_name = team["name"]
        weekly_summary = []
        
        for week in range(1, 14):
            week_str = str(week)
            week_matchups = weekly_scores.get(week_str, [])
            team_score = "N/A"
            opponent = "N/A"
            opponent_score = "N/A"
            outcome = "N/A"
            
            for matchup in week_matchups:
                if team_name == matchup["home_team"]:
                    team_score = matchup["home_score"]
                    opponent = matchup["away_team"]
                    opponent_score = matchup["away_score"]
                    if team_score > opponent_score:
                        outcome = "Win"
                    elif team_score < opponent_score:
                        outcome = "Loss"
                    else:
                        outcome = "Tie"
                    break
                elif team_name == matchup["away_team"]:
                    team_score = matchup["away_score"]
                    opponent = matchup["home_team"]
                    opponent_score = matchup["home_score"]
                    if team_score > opponent_score:
                        outcome = "Win"
                    elif team_score < opponent_score:
                        outcome = "Loss"
                    else:
                        outcome = "Tie"
                    break
            
            weekly_summary.append({
                "week": week,
                "score": team_score,
                "opponent": opponent,
                "opponent_score": opponent_score,
                "outcome": outcome
            })
        
        team_weekly_summaries[team_name] = weekly_summary

    return render_template("year.html", year=year, teams=teams, 
                         team_weekly_summaries=team_weekly_summaries, 
                         overall_records=overall_records)

@app.route('/year_standings/<int:year>')
def year_standings(year):
    year_data = league_data.get(str(year), {})
    teams = sorted(year_data.get("teams", []), key=lambda x: x.get("rank", float('inf')))
    return render_template("year_standings.html", year=year, teams=teams)

@app.route('/head_to_head')
def head_to_head_view():
    head_to_head = calculate_historical_head_to_head()
    owners = sorted(head_to_head.keys())
    return render_template("head_to_head.html", head_to_head=head_to_head, owners=owners)

@app.route("/power_rankings")
def power_rankings():
    """Renders the power rankings page with total points scored section."""
    rankings = get_power_rankings()
    overall_records = calculate_overall_records()  # Calculate overall records
    print("DEBUG: Active Rankings:", rankings["active"])  # Debug active rankings
    print("DEBUG: Retired Rankings:", rankings["retired"])  # Debug retired rankingss
    print("DEBUG: Points Scored Rankings:", rankings["points_scored"])  # Debug points scored rankings

    # Calculate average finish for each owner
    average_finish = {}
    for year, data in league_data.items():
        for team in data.get("teams", []):
            owner = team.get("owner", "Unknown")
            rank = team.get("rank", float('inf'))
            if owner not in average_finish:
                average_finish[owner] = []
            average_finish[owner].append(rank)

    for owner in average_finish:
        average_finish[owner] = sum(average_finish[owner]) / len(average_finish[owner])

    return render_template("power_rankings.html", 
                           active_rankings=rankings["active"], 
                           retired_rankings=rankings["retired"],
                           points_scored=rankings["points_scored"],
                           overall_records=overall_records,
                           average_finish=average_finish)

# In-memory storage for chat messages and users
chat_messages = []
users = {}

@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if request.method == 'POST':
        username = request.json.get('username')
        pin = request.json.get('pin')
        message = request.json.get('message')

        # Validate username and PIN
        if 'username' not in session:
            if username in users and users[username] != pin:
                return jsonify({"error": "Invalid PIN for this username."}), 403

            # Register new user if not already registered
            if username not in users:
                users[username] = pin

            # Save username in session
            session['username'] = username

        # Use session username for messages
        username = session['username']

        # Add the message to the chat log with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        chat_entry = {"username": username, "message": message, "timestamp": timestamp}

        # Append to in-memory chat messages
        chat_messages.append(chat_entry)

        # Write to chat log file
        with open(CHAT_LOG_FILE, "r+") as f:
            chat_log = json.load(f)
            chat_log.append(chat_entry)
            f.seek(0)
            json.dump(chat_log, f, indent=4)

        return jsonify({"success": True})

    # Render the chat.html template for GET requests
    return render_template("chat.html")

@app.route('/get_messages', methods=['GET'])
def get_messages():
    try:
        with open('chat_log.json', 'r') as file:
            messages = json.load(file)
        return jsonify(messages)
    except FileNotFoundError:
        return jsonify([])  # Return an empty list if the file doesn't exist
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Flask app configuration
if __name__ == "__main__":
    try:
        app.run(debug=False, use_reloader=False)  # Disable debug mode for production
    except (KeyboardInterrupt, SystemExit):
        pass