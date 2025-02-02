import pandas as pd
import random
import copy
import math


def generate_initial_schedule(teams, incidents):
    # Sort incidents by severity (high to low)
    incidents = incidents.sort_values(by="severity", ascending=False).reset_index(drop=True)

    # Sort teams: First by variety of crime types, then by power
    teams['crime_type_count'] = teams['crime_types'].apply(lambda x: len(x.split(';')))
    teams = teams.sort_values(by=['crime_type_count', 'power']).reset_index(drop=True)
    teams = teams.drop(columns=['crime_type_count'])  # Remove helper column

    initial_schedule = pd.DataFrame(columns=["incident", "assigned_team"])

    # Assign teams to incidents
    for i, incident in incidents.iterrows():
        if incident['status'] == 'open':
            for j, team in teams.iterrows():
                if (incident['crime_type'] in team['crime_types']
                        and team['units_available'] * team['power'] >= incident['severity']):

                    # Update available units
                    teams.at[j, 'units_available'] = team['units_available'] - math.ceil(incident['severity'] / team['power'])

                    # Update incident status
                    incidents.at[i, 'status'] = "in_progress"

                    # Update schedule
                    initial_schedule = pd.concat([initial_schedule, pd.DataFrame({
                        "incident": [incident['location']],
                        "assigned_team": [team['team_name']]})], ignore_index=True)
                    break  # Move to the next incident after assignment

    return initial_schedule




def evaluate_solution(teams, incidents, assignment):
    """
    Compute the total penalty of an assignment.

    Rules:
      - If incident is assigned to no team (None) or a team that doesn't cover the crime:
        large penalty (9999)
      - Otherwise, penalty = max(0, severity - team_power).

    :param teams: list of dicts
    :param incidents: list of dicts
    :param assignment: dict {incident_id: team_name}
    :return: float (total penalty)
    """
    # Create lookup by team_name
    team_lookup = {t["team_name"]: t for t in teams}

    total_penalty = 0.0
    for inc in incidents:
        inc_id = inc["incident_id"]
        assigned_team = assignment.get(inc_id, None)

        if not assigned_team:
            # No team -> large penalty
            total_penalty += 9999
            continue

        team = team_lookup[assigned_team]
        # Check coverage
        if inc["crime_type"] not in team["crime_types"]:
            total_penalty += 9999
        else:
            # penalty = max(0, severity - power)
            sev = inc["severity"]
            pwr = team["power"]
            penalty = max(0, sev - pwr)
            total_penalty += penalty

    return total_penalty


def refine_solution(teams, incidents, assignment, max_iterations=1000):
    """
    Attempt local improvements by randomly reassigning an incident.
    If a random reassignment improves penalty, accept it.

    :param teams: list of dicts
    :param incidents: list of dicts
    :param assignment: dict {incident_id: team_name}
    :param max_iterations: how many random attempts to make
    :return: improved assignment (dict)
    """
    best_assignment = copy.deepcopy(assignment)
    best_penalty = evaluate_solution(teams, incidents, best_assignment)

    # Precompute which teams can handle each crime type
    crime_to_teams = {}
    for t in teams:
        for ctype in t["crime_types"]:
            crime_to_teams.setdefault(ctype, []).append(t["team_name"])

    # Track how many units each team is currently using in best_assignment
    units_left = {t["team_name"]: t["units_available"] for t in teams}
    for inc in incidents:
        inc_id = inc["incident_id"]
        assigned = best_assignment[inc_id]
        if assigned in units_left and assigned is not None:
            units_left[assigned] -= 1

    for _ in range(max_iterations):
        # Pick a random incident
        inc = random.choice(incidents)
        inc_id = inc["incident_id"]
        old_team = best_assignment[inc_id]

        # 'Release' the old team's unit
        if old_team is not None:
            units_left[old_team] += 1

        # Which teams can handle this?
        valid_teams = crime_to_teams.get(inc["crime_type"], [])
        feasible_teams = [tm for tm in valid_teams if units_left[tm] > 0]

        if not feasible_teams:
            # revert usage
            if old_team is not None:
                units_left[old_team] -= 1
            continue

        # pick a random new team
        new_team = random.choice(feasible_teams)

        # new assignment
        new_assignment = copy.deepcopy(best_assignment)
        new_assignment[inc_id] = new_team

        new_penalty = evaluate_solution(teams, incidents, new_assignment)

        if new_penalty < best_penalty:
            # accept improvement
            best_assignment = new_assignment
            best_penalty = new_penalty
            units_left[new_team] -= 1
        else:
            # revert usage
            if old_team is not None:
                units_left[old_team] -= 1

    return best_assignment


def monte_carlo_solution(teams, incidents, num_iterations=50, refine_iters=200):
    """
    Repeatedly:
      - generate a random solution
      - refine it
      - keep track of the best
    """
    best_assignment = None
    best_penalty = float('inf')

    for _ in range(num_iterations):
        init_sol = generate_initial_schedule(teams, incidents)
        refined_sol = refine_solution(teams, incidents, init_sol, max_iterations=refine_iters)
        penalty = evaluate_solution(teams, incidents, refined_sol)

        if penalty < best_penalty:
            best_penalty = penalty
            best_assignment = refined_sol

    return best_assignment, best_penalty

def main():

    teams = pd.read_csv("teams.csv")
    incidents = pd.read_csv("incidents.csv")
    incidents = incidents[incidents["status"].isin(["open", "in_progress"])]

    initial_schedule = generate_initial_schedule(teams, incidents)
    print(initial_schedule)




'''
def main():
    # ============ 1) READ TEAMS CSV with pandas ============
    teams_df = pd.read_csv("teams.csv")
    # Expected columns: team_name, units_available, total_units, power, crime_types

    # Convert each row to a dict with the structure used in the solver
    teams = []
    for _, row in teams_df.iterrows():
        # crime_types: split by semicolon
        crime_set = set(str(row["crime_types"]).split(";"))

        team_dict = {
            "team_name": row["team_name"],
            "units_available": int(row["units_available"]),
            "total_units": int(row["total_units"]),
            "power": float(row["power"]),
            "crime_types": crime_set
        }
        teams.append(team_dict)

    # ============ 2) READ INCIDENT CSV with pandas ============
    incidents_df = pd.read_csv("incident.csv")
    # Expected columns: incident_id, status, crime_type, severity

    # Filter to only "open" or "in_progress"
    active_incidents_df = incidents_df[incidents_df["status"].isin(["open", "in_progress"])].copy()

    # Convert each row to a dict
    incidents = []
    for _, row in active_incidents_df.iterrows():
        inc_dict = {
            "incident_id": row["incident_id"],
            "status": row["status"],
            "crime_type": row["crime_type"],
            "severity": float(row["severity"])  # or int(...) if always integer
        }
        incidents.append(inc_dict)

    # ============ 3) Run Monte Carlo ============
    best_assign, best_penalty = monte_carlo_solution(
        teams,
        incidents,
        num_iterations=50,
        refine_iters=200
    )

    # ============ 4) Print Results ============
    print("Best penalty found:", best_penalty)
    print("Assignments:")
    # Sort incidents by incident_id for nicer display
    incidents_sorted = sorted(incidents, key=lambda x: x["incident_id"])
    for inc in incidents_sorted:
        inc_id = inc["incident_id"]
        tname = best_assign.get(inc_id, None)
        print(f"  {inc_id} -> {tname}")

    # Also print as CSV lines
    print("\nCSV output (incident_id,team_name):")
    print("incident_id,team_name")
    for inc in incidents_sorted:
        inc_id = inc["incident_id"]
        tname = best_assign.get(inc_id, "")
        print(f"{inc_id},{tname}")
'''

if __name__ == "__main__":
    main()
