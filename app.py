import numpy as np
import pandas as pd
import random
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')

# You could tweak these “weights” to emphasize certain objectives
BIG_PENALTY = 999999
WORKLOAD_BALANCE_WEIGHT = 10.0  # just an example
SEVERITY_WEIGHT = 1.0


def generate_initial_solution(teams_df, incidents_df):
    """
    Generate a 'naive' or 'random' initial assignment of teams to incidents.
    We return a copy of incidents_df with a new column 'assigned_team'.
    """
    # Convert to a DataFrame we can modify
    solution_df = incidents_df.copy()
    solution_df['assigned_team'] = None

    # For unit tracking, create a dict: {team_name: units_left}
    team_units_left = dict(zip(teams_df['team_name'], teams_df['units_available']))

    # Create a dict for quickly seeing which crime_types each team can handle
    # e.g. { "Alpha": set(["Theft","Assault"]), ... }
    teams_crime_map = {}
    for idx, row in teams_df.iterrows():
        team_name = row['team_name']
        crime_types = set(str(row['crime_types']).split(';'))
        teams_crime_map[team_name] = crime_types

    # For each incident, pick a random feasible team
    for idx, inc_row in solution_df.iterrows():
        crime_type = inc_row['crime_type']

        # Filter teams that can handle this crime_type AND have units left
        feasible_teams = []
        for t_idx, t_row in teams_df.iterrows():
            t_name = t_row['team_name']
            if crime_type in teams_crime_map[t_name] and team_units_left[t_name] > 0:
                feasible_teams.append(t_name)

        if not feasible_teams:
            # No feasible team -> assigned_team = None (this will yield big penalty)
            solution_df.at[idx, 'assigned_team'] = None
        else:
            chosen_team = random.choice(feasible_teams)
            solution_df.at[idx, 'assigned_team'] = chosen_team
            team_units_left[chosen_team] -= 1

    return solution_df


def evaluate_solution(teams_df, solution_df):
    """
    Compute the total 'cost' or 'penalty' of the solution.

    A possible penalty:
      - If 'assigned_team' is None or not covering crime -> add BIG_PENALTY
      - Otherwise penalty = max(0, severity - team_power) * SEVERITY_WEIGHT
      - Optionally, add 'workload balance' cost.
        e.g. standard deviation of #incidents/team multiplied by WORKLOAD_BALANCE_WEIGHT
    """
    # Make a lookup for team power, crime_types
    team_power = dict(zip(teams_df['team_name'], teams_df['power']))
    team_crimes = {}
    for idx, row in teams_df.iterrows():
        team_crimes[row['team_name']] = set(str(row['crime_types']).split(';'))

    # Count incidents per team to measure workload
    assigned_counts = {}
    for t_name in teams_df['team_name']:
        assigned_counts[t_name] = 0

    total_penalty = 0.0

    for idx, inc_row in solution_df.iterrows():
        assigned_team = inc_row['assigned_team']
        crime_type = inc_row['crime_type']
        severity = inc_row['severity']

        if not assigned_team or assigned_team not in team_crimes:
            total_penalty += BIG_PENALTY
        else:
            # Check if team covers the crime
            if crime_type not in team_crimes[assigned_team]:
                total_penalty += BIG_PENALTY
            else:
                # penalty = max(0, severity - power)
                power = team_power[assigned_team]
                penalty = max(0, severity - power) * SEVERITY_WEIGHT
                total_penalty += penalty
                assigned_counts[assigned_team] += 1

    # Workload balance cost: standard deviation of assigned_counts
    counts_array = np.array(list(assigned_counts.values()))
    std_dev = np.std(counts_array)
    workload_balance_cost = std_dev * WORKLOAD_BALANCE_WEIGHT
    total_penalty += workload_balance_cost

    return total_penalty


def refine_solution(teams_df, solution_df, max_iterations=100):
    """
    Try to locally improve the solution by random reassignments or swaps.
    If a change improves cost, keep it.
    Return the best solution found.
    """
    best_df = solution_df.copy()
    best_cost = evaluate_solution(teams_df, best_df)

    for _ in range(max_iterations):
        # We'll create a copy
        new_df = best_df.copy()

        # Randomly pick an incident to reassign
        incident_to_change = random.randint(0, len(new_df) - 1)
        new_df = new_df.reset_index(drop=True)

        # Reassign to a random feasible team (like in 'generate_initial_solution')
        inc_crime_type = new_df.loc[incident_to_change, 'crime_type']

        # We'll do a quick check of teams that *could* handle this if they have units left
        # but we also need to recalc units usage in 'new_df' to see if there's a free slot
        used_units = {t: 0 for t in teams_df['team_name']}
        for i, row in new_df.iterrows():
            at = row['assigned_team']
            if at in used_units and at is not None:
                used_units[at] += 1

        feasible_teams = []
        for idx, t_row in teams_df.iterrows():
            t_name = t_row['team_name']
            t_crimes = set(str(t_row['crime_types']).split(';'))
            if inc_crime_type in t_crimes:
                # check if we have leftover capacity
                if used_units[t_name] < t_row['units_available']:
                    feasible_teams.append(t_name)

        if not feasible_teams:
            # If no feasible teams, skip
            continue

        old_team = new_df.loc[incident_to_change, 'assigned_team']
        new_team = random.choice(feasible_teams)

        # Make the change
        new_df.loc[incident_to_change, 'assigned_team'] = new_team

        # Evaluate
        new_cost = evaluate_solution(teams_df, new_df)
        if new_cost < best_cost:
            best_df = new_df.copy()
            best_cost = new_cost

    return best_df


def single_solution_monte_carlo(teams_df, incidents_df, max_iterations=10):
    """
    A simple approach that:
      1) Generates an initial solution
      2) Iterates refine_solution multiple times
      3) Keeps track of the best so far
    """
    current_solution = generate_initial_solution(teams_df, incidents_df)
    current_cost = evaluate_solution(teams_df, current_solution)

    best_solution = current_solution.copy()
    best_cost = current_cost

    for iteration in range(max_iterations):
        # Attempt a refine
        refined_solution = refine_solution(teams_df, current_solution, max_iterations=1000)
        refined_cost = evaluate_solution(teams_df, refined_solution)

        # Accept if better
        if refined_cost < best_cost:
            best_cost = refined_cost
            best_solution = refined_solution.copy()

        # Move forward
        current_solution = refined_solution.copy()

        logging.info(f"Iteration {iteration + 1}/{max_iterations}: Best Cost = {best_cost}")

    return best_solution, best_cost


def main():
    # ========== 1) READ TEAMS CSV ==========
    teams_file = "large_teams.csv"
    teams_df = pd.read_csv(teams_file)
    # columns expected: team_name, units_available, total_units, power, crime_types

    # ========== 2) READ INCIDENTS CSV ==========
    incidents_file = "large_incidents.csv"
    incidents_df = pd.read_csv(incidents_file)
    # columns expected: incident_id, status, crime_type, severity

    # Filter to only open / in_progress
    incidents_df = incidents_df[incidents_df['status'].isin(['open', 'in_progress'])].copy()

    # ========== 3) RUN SINGLE-SOLUTION MONTE CARLO ==========
    best_solution_df, best_cost = single_solution_monte_carlo(
        teams_df,
        incidents_df,
        max_iterations=10  # you can increase
    )

    logging.info(f"Best overall cost found: {best_cost}")

    # ========== 4) OUTPUT THE BEST SOLUTION ==========
    # best_solution_df has columns: incident_id, status, crime_type, severity, assigned_team
    # You can save it to CSV:
    best_solution_df.to_csv("best_assignment.csv", index=False)

    logging.info("Sample of best solution:")
    logging.info(best_solution_df.head(10))


if __name__ == "__main__":
    main()
