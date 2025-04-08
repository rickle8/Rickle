import requests
import json
from espn_api.football import League
from flask import Flask, render_template
from datetime import datetime

# League credentials
LEAGUE_ID = 113291
SWID = "{903ae7c0-152e-47ad-bea0-5687394e70e4}"
ESPN_S2 = "AEC6yNOCVgO57OcmEA2X9IvSO1n82PucryWA1Tyl7vL0vhEB13P1zVDThUGlTEY0lp2tO6KaXnuwY%2FE0la36PcJO9smK3EeRA%2FlqK5nErEIic2g6SqdaByQQVy9fUG0swQDQMAKeCCwxzWll4K3FxTdwrfvDLTz%2FICycfI1tzun6w0gT1Y%2BAcKDQ0MYwk%2BJCAn4dpPWWECOBq1meiagzmFWbJNMPB5VpwKXV5x72Pa92rEWZcJtidU1O3RW6Rs7G4%2B6tc8ky8Sw1IbcNmqM%2FyKrB"
YEARS = range(2014, 2025)

def get_league_data(year):
    """Fetches league data for a specific year using ESPN API."""
    try:
        league = League(league_id=LEAGUE_ID, year=year, espn_s2=ESPN_S2, swid=SWID)
        print(f"Successfully fetched data for {year}")
        return league
    except Exception as e:
        print(f"Error fetching data for {year}: {str(e)}")
        return None

def calculate_head_to_head(league):
    """Calculates head-to-head records for all owners in the league."""
    head_to_head = {}
    for week in range(1, 15):
        try:
            matchups = league.scoreboard(week=week)
            for matchup in matchups:
                home_team = matchup.home_team
                away_team = matchup.away_team
                home_owner = home_team.owners[0]['firstName'] + ' ' + home_team.owners[0]['lastName'] if home_team.owners else f"Unknown_{home_team.team_id}"
                away_owner = away_team.owners[0]['firstName'] + ' ' + away_team.owners[0]['lastName'] if away_team.owners else f"Unknown_{away_team.team_id}"
                
                if home_owner not in head_to_head:
                    head_to_head[home_owner] = {}
                if away_owner not in head_to_head:
                    head_to_head[away_owner] = {}
                
                if matchup.home_score > matchup.away_score:
                    head_to_head[home_owner].setdefault(away_owner, {"wins": 0, "losses": 0, "ties": 0})["wins"] += 1
                    head_to_head[away_owner].setdefault(home_owner, {"wins": 0, "losses": 0, "ties": 0})["losses"] += 1
                elif matchup.away_score > matchup.home_score:
                    head_to_head[home_owner].setdefault(away_owner, {"wins": 0, "losses": 0, "ties": 0})["losses"] += 1
                    head_to_head[away_owner].setdefault(home_owner, {"wins": 0, "losses": 0, "ties": 0})["wins"] += 1
                else:
                    head_to_head[home_owner].setdefault(away_owner, {"wins": 0, "losses": 0, "ties": 0})["ties"] += 1
                    head_to_head[away_owner].setdefault(home_owner, {"wins": 0, "losses": 0, "ties": 0})["ties"] += 1
        except:
            print(f"No data for week {week} in {league.year}")
    return head_to_head

def build_json():
    league_history = {}
    for year in YEARS:
        print(f"Fetching data for {year}...")
        league = get_league_data(year)
        if not league:
            continue
        
        teams = []
        try:
            standings = league.standings()
            for rank, team in enumerate(standings, 1):
                games_played = team.wins + team.losses + team.ties
                avg_points_for = team.points_for / games_played if games_played > 0 else 0
                avg_points_against = team.points_against / games_played if games_played > 0 else 0
                point_differential = avg_points_for - avg_points_against
                
                owner_name = (team.owners[0]['firstName'] + ' ' + team.owners[0]['lastName']) if team.owners else f"Unknown_{team.team_id}"
                
                team_data = {
                    "name": team.team_name,
                    "team_id": team.team_id,
                    "owner": owner_name,
                    "wins": team.wins,
                    "losses": team.losses,
                    "ties": team.ties,
                    "points_for": team.points_for,
                    "points_against": team.points_against,
                    "avg_points_for": round(avg_points_for, 1),
                    "avg_points_against": round(avg_points_against, 1),
                    "point_differential": round(point_differential, 1),
                    "rank": rank,
                    "roster": [{"name": player.name, "position": player.position} for player in team.roster]
                }
                teams.append(team_data)
        except AttributeError:
            print(f"Warning: league.standings() not available for {year}. Falling back to default team order.")
            for i, team in enumerate(league.teams, 1):
                games_played = team.wins + team.losses + team.ties
                avg_points_for = team.points_for / games_played if games_played > 0 else 0
                avg_points_against = team.points_against / games_played if games_played > 0 else 0
                point_differential = avg_points_for - avg_points_against
                
                owner_name = (team.owners[0]['firstName'] + ' ' + team.owners[0]['lastName']) if team.owners else f"Unknown_{i}"
                
                team_data = {
                    "name": team.team_name,
                    "team_id": team.team_id,
                    "owner": owner_name,
                    "wins": team.wins,
                    "losses": team.losses,
                    "ties": team.ties,
                    "points_for": team.points_for,
                    "points_against": team.points_against,
                    "avg_points_for": round(avg_points_for, 1),
                    "avg_points_against": round(avg_points_against, 1),
                    "point_differential": round(point_differential, 1),
                    "rank": i,
                    "roster": [{"name": player.name, "position": player.position} for player in team.roster]
                }
                teams.append(team_data)
        
        head_to_head = calculate_head_to_head(league)
        
        # Add weekly scores with matchups
        weekly_scores = {}
        for week in range(1, 14):  # Assuming 13-week regular season
            try:
                matchups = league.scoreboard(week=week)
                weekly_scores[str(week)] = [
                    {
                        "home_team": matchup.home_team.team_name,
                        "away_team": matchup.away_team.team_name,
                        "home_score": matchup.home_score,
                        "away_score": matchup.away_score
                    }
                    for matchup in matchups
                ]
            except Exception as e:
                print(f"No scoreboard data for week {week} in {year}: {str(e)}")
                weekly_scores[str(week)] = []
        
        league_history[str(year)] = {
            "teams": teams,
            "weekly_scores": weekly_scores,
            "head_to_head": head_to_head
        }
    
    # Add retired league member James Mitchell Hynes
    retired_member = {
        "name": "James Mitchell Hynes",
        "status": "Retired",
        "note": "Banned for illegal transactions ☠️🪦"
    }
    league_history["retired_members"] = league_history.get("retired_members", [])
    league_history["retired_members"].append(retired_member)
    
    with open("league_history.json", "w") as f:
        json.dump(league_history, f, indent=4)
    print("Updated league_history.json created successfully!")

if __name__ == "__main__":
    build_json()  # Generate JSON by default