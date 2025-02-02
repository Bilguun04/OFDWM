import csv
import random
import copy

def generate_initial_solution(teams, incidents):
    """
    Generate a random feasible assignment of teams to incidents.
    Each incident is assigned to exactly one team that can handle it
    AND still has at least 1 unit available.
    Returns: dict {incident_id: team_name}
    """
    # Keep track of how many units are left for each team
    units_left = {team["team_name"]: team["units_available"] for team in teams}

    assignment = {}
    for inc in incidents:
        incident_id = inc["incident_id"]
        crime_type = inc["crime_type"]

        # Find teams that can handle this crime_type and have units left
        valid_teams = []
        for team in teams:
            if crime_type in team["crime_types"] and units_left[team["team_name"]] > 0:
                valid_teams.append(team["team_name"])

        if not valid_teams:
            # No valid team available; use None or add big penalty
            assignment[incident_id] = None
        else:
            chosen = random.choice(valid_teams)
            assignment[incident_id] = chosen
            units_left[chosen] -= 1

    return assignment


def evaluate_solution(teams, incidents, assignment):
    """
    Compute the total penalty of an assignment.
    Penalty rule:
      - If no team assigned OR crime_type not covered by that team -> big penalty (9999).
      - Otherwise, penalty = max(0, severity - team_power).
    """
    # Create a lookup by team_name
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
            # Calculate penalty = max(0, severity - power)
            severity = inc["severity"]
            power = team["power"]
            penalty = max(0, severity - power)
            total_penalty += penalty

    return total_penalty


def refine_solution(teams, incidents, assignment, max_iterations=1000):
    """
    Attempt local improvements by reassigning incidents randomly.
    If a random reassignment decreases penalty, we keep it.

    Returns an improved assignment (dict) after up to max_iterations tries.
    """
    best_assignment = copy.deepcopy(assignment)
    best_penalty = evaluate_solution(teams, incidents, best_assignment)

    # Precompute teams that can handle each crime type
    crime_to_teams = {}
    for t in teams:
        for ctype in t["crime_types"]:
            crime_to_teams.setdefault(ctype, []).append(t["team_name"])

    # Track how many units left for each team in best_assignment
    units_left = {t["team_name"]: t["units_available"] for t in teams}
    for inc in incidents:
        tid = best_assignment[inc["incident_id"]]
        if tid in units_left and tid is not None:
            units_left[tid] -= 1

    for _ in range(max_iterations):
        # Pick a random incident to try changing
        inc = random.choice(incidents)
        inc_id = inc["incident_id"]
        old_team = best_assignment[inc_id]

        # Release the unit from the old_team (if any)
        if old_team is not None:
            units_left[old_team] += 1

        # Possible teams that can handle this incident's crime_type
        valid_teams = crime_to_teams.get(inc["crime_type"], [])
        # Among those, which have units left?
        feasible_teams = [tm for tm in valid_teams if units_left[tm] > 0]

        if not feasible_teams:
            # revert usage
            if old_team is not None:
                units_left[old_team] -= 1
            continue

        # Pick a random feasible team
        new_team = random.choice(feasible_teams)

        # Make a copy of the assignment
        new_assignment = copy.deepcopy(best_assignment)
        new_assignment[inc_id] = new_team

        new_penalty = evaluate_solution(teams, incidents, new_assignment)

        if new_penalty < best_penalty:
            # Accept the new assignment
            best_assignment = new_assignment
            best_penalty = new_penalty
            # Commit the usage
            units_left[new_team] -= 1
        else:
            # Revert usage
            if old_team is not None:
                units_left[old_team] -= 1

    return best_assignment


def monte_carlo_solution(teams, incidents, num_iterations=50, refine_iters=200):
    """
    Repeatedly:
      1. Generate a random initial solution
      2. Refine it
      3. Keep track of the best solution across many trials
    """
    best_assignment = None
    best_penalty = float('inf')

    for _ in range(num_iterations):
        # Generate
        init_solution = generate_initial_solution(teams, incidents)
        # Refine
        refined_sol = refine_solution(teams, incidents, init_solution, max_iterations=refine_iters)
        # Evaluate
        penalty = evaluate_solution(teams, incidents, refined_sol)

        if penalty < best_penalty:
            best_penalty = penalty
            best_assignment = refined_sol

    return best_assignment, best_penalty


def main():
    # ============ 1) READ TEAMS FROM CSV ============
    teams = []
    with open('teams.csv', 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Parse numeric fields
            units_available = int(row['units_available'])
            total_units = int(row['total_units'])
            power = float(row['power'])
            # Parse crime_types: split by semicolon
            raw_crimes = row['crime_types'].split(';')
            crimeset = {c.strip() for c in raw_crimes}

            team_info = {
                "team_name": row['team_name'],
                "units_available": units_available,
                "total_units": total_units,
                "power": power,
                "crime_types": crimeset
            }
            teams.append(team_info)

    # ============ 2) READ INCIDENTS FROM CSV ============
    all_incidents = []
    with open('incident.csv', 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            incident_id = row['incident_id']
            status = row['status']
            crime_type = row['crime_type']
            severity = float(row['severity'])  # or int if always integer

            inc_info = {
                "incident_id": incident_id,
                "status": status,
                "crime_type": crime_type,
                "severity": severity
            }
            all_incidents.append(inc_info)

    # ============ 3) FILTER ONLY 'open' OR 'in_progress' INCIDENTS ============
    active_incidents = [inc for inc in all_incidents
                        if inc["status"] in ("open", "in_progress")]

    # ============ 4) RUN MONTE CARLO SOLUTION ============
    best_assign, best_penalty = monte_carlo_solution(teams, active_incidents,
                                                     num_iterations=50,
                                                     refine_iters=200)

    # ============ 5) PRINT RESULTS ============
    print("Best penalty found:", best_penalty)
    print("Assignments (incident -> team_name):")
    for inc in sorted(active_incidents, key=lambda x: x["incident_id"]):
        i_id = inc["incident_id"]
        assigned_team = best_assign.get(i_id, None)
        print(f"  {i_id} -> {assigned_team}")

    # Also print as CSV for the *active* incidents only
    print("\nCSV output (incident_id,team_name):")
    print("incident_id,team_name")
    for inc in sorted(active_incidents, key=lambda x: x["incident_id"]):
        i_id = inc["incident_id"]
        assigned_team = best_assign.get(i_id, "")
        print(f"{i_id},{assigned_team}")


if __name__ == "__main__":
    main()
