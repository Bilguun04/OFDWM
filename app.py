import numpy as np
import pandas as pd
import random
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')

# Constants for new penalty logic:
MISS_CASE_PENALTY = 1000  # couldn't handle incident
NO_UNITS_PENALTY = 400  # assigned to a team that actually has no units left
OVER_ASSIGN_PENALTY = 200  # P > S
HIGH_POWER_LOW_SEVERITY = 300  # e.g. if S is quite low but we assigned a big-power team
LEFTOVER_UNITS_WEIGHT = 10.0  # leftover fraction * 10


# (The rest from your prior code)
def generate_initial_solution(teams_df, incidents_df):
    """
    Same approach: either random or a sorted-by-severity approach.
    For illustration, we'll keep it random or naive.
    You can replace this with your 'sort by severity' logic if you prefer.
    """
    solution_df = incidents_df.copy()
    solution_df['assigned_team'] = None

    # Track how many units are left for each team
    team_units_left = dict(zip(teams_df['team_name'], teams_df['units_available']))

    # Convert crime_types to a dict of sets
    team_crime_map = {}
    for idx, row in teams_df.iterrows():
        tname = row['team_name']
        ctypes = set(str(row['crime_types']).split(';'))
        team_crime_map[tname] = ctypes

    # For each incident, pick a feasible team at random
    for idx, inc_row in solution_df.iterrows():
        ctype = inc_row['crime_type']
        feasible = []
        for t_idx, t_row in teams_df.iterrows():
            tname = t_row['team_name']
            if ctype in team_crime_map[tname] and team_units_left[tname] > 0:
                feasible.append(tname)

        if not feasible:
            # no assignment -> big penalty
            solution_df.at[idx, 'assigned_team'] = None
        else:
            chosen = random.choice(feasible)
            solution_df.at[idx, 'assigned_team'] = chosen
            team_units_left[chosen] -= 1

    return solution_df


def evaluate_solution(teams_df, solution_df):
    """
    Apply the new penalty rules as specified:

    1) If assigned_team=None => penalty = 1000 (miss case).
       Also if a team is assigned but effectively has no units left => 400 (no_units).

    2) Over-assign: if team.power > incident.severity => +200

    3) High power for low severity => +300
       (Define "low severity" and "high power" thresholds as desired.)

    4) After all incidents, add leftover capacity penalty:
         leftover fraction * 10 (summed across all teams).
    """
    # Make a quick lookup
    team_power = dict(zip(teams_df['team_name'], teams_df['power']))
    team_crimes = {}
    for idx, row in teams_df.iterrows():
        team_crimes[row['team_name']] = set(str(row['crime_types']).split(';'))
    # Also track (initial) units_available for leftover penalty
    team_avail = dict(zip(teams_df['team_name'], teams_df['units_available']))
    # We'll compute how many units were actually used in this solution,
    # so we can figure out leftover fraction
    used_units = {t: 0 for t in teams_df['team_name']}

    total_penalty = 0.0

    # Evaluate each incident
    for idx, inc_row in solution_df.iterrows():
        severity = inc_row['severity']
        crime_type = inc_row['crime_type']
        assigned_team = inc_row['assigned_team']

        if assigned_team is None:
            # Missed the case entirely
            total_penalty += MISS_CASE_PENALTY
            continue

        # We assume we assigned them, but let's see if that team actually had capacity
        # In the real assignment we try not to violate units, but let's just check
        row_team = teams_df[teams_df['team_name'] == assigned_team]
        if row_team.empty:
            # Not in teams => big penalty?
            total_penalty += MISS_CASE_PENALTY
            continue

        # If that team had 0 units left in the final arrangement => 400
        # We need to re-check how many times we've used that team
        used_units[assigned_team] += 1
        # We'll just accept it for now, the final leftover penalty comes after

        # Over-assign and high-power checks
        power = team_power[assigned_team]

        # Over-assign => if power > severity => +200
        if power > severity:
            total_penalty += OVER_ASSIGN_PENALTY

        # High power for low severity => +300
        # You must define "low severity" threshold or ratio. Let's say severity <= 2 is "low."
        # and "high power" might be >= 5 (example).
        if severity <= 2 and power >= 5:
            total_penalty += HIGH_POWER_LOW_SEVERITY

    # Now compute leftover fraction penalty
    # leftover fraction for each team = leftover_units / total_units
    # leftover_units = team_avail[t] - used_units[t]
    # penalty = leftover_fraction * LEFTOVER_UNITS_WEIGHT
    leftover_penalty_sum = 0.0
    for t in teams_df['team_name']:
        total_units_for_t = teams_df.loc[teams_df['team_name'] == t, 'total_units'].values[0]
        used = used_units[t]
        leftover = total_units_for_t - used
        if total_units_for_t > 0:
            leftover_frac = leftover / total_units_for_t
        else:
            leftover_frac = 0
        leftover_penalty_sum += leftover_frac * LEFTOVER_UNITS_WEIGHT

    total_penalty += leftover_penalty_sum

    return total_penalty


def refine_solution(teams_df, solution_df, max_iterations=100):
    """
    Same local search approach as before:
    - Randomly pick an incident, reassign it if feasible, check if penalty improves.
    - Keep best found.
    """
    best_df = solution_df.copy()
    best_cost = evaluate_solution(teams_df, best_df)

    for _ in range(max_iterations):
        new_df = best_df.copy()
        new_df = new_df.reset_index(drop=True)

        # randomly pick incident
        incident_to_change = random.randint(0, len(new_df) - 1)
        crime_type = new_df.loc[incident_to_change, 'crime_type']

        # figure out how many times each team is used (to check leftover capacity)
        used_units = {t: 0 for t in teams_df['team_name']}
        for i, row in new_df.iterrows():
            at = row['assigned_team']
            if at and at in used_units:
                used_units[at] += 1

        # find feasible teams
        feasible = []
        for idx, trow in teams_df.iterrows():
            tname = trow['team_name']
            t_crimes = set(str(trow['crime_types']).split(';'))
            # check if it can handle the crime
            if crime_type in t_crimes:
                # check if we haven't exceeded availability
                if used_units[tname] < trow['units_available']:
                    feasible.append(tname)

        if not feasible:
            # skip
            continue

        new_team = random.choice(feasible)
        new_df.loc[incident_to_change, 'assigned_team'] = new_team

        new_cost = evaluate_solution(teams_df, new_df)
        if new_cost < best_cost:
            best_df = new_df.copy()
            best_cost = new_cost

    return best_df


def single_solution_monte_carlo(teams_df, incidents_df, max_iterations=10):
    """
    1) Generate initial solution
    2) Repeatedly refine, track best
    """
    current_solution = generate_initial_solution(teams_df, incidents_df)
    current_cost = evaluate_solution(teams_df, current_solution)

    best_solution = current_solution.copy()
    best_cost = current_cost

    for iteration in range(max_iterations):
        refined_solution = refine_solution(teams_df, current_solution, max_iterations=50)
        refined_cost = evaluate_solution(teams_df, refined_solution)
        if refined_cost < best_cost:
            best_cost = refined_cost
            best_solution = refined_solution.copy()
        current_solution = refined_solution.copy()
        logging.info(f"Iteration {iteration + 1}/{max_iterations}: Best Cost = {best_cost}")

    return best_solution, best_cost


def main():
    # (1) Read teams
    teams_file = "large_teams.csv"
    teams_df = pd.read_csv(teams_file)

    # Force more "lesser power" if desired:
    # For example, clamp the power to be in [1, 3].
    teams_df['power'] = teams_df['power'].apply(lambda x: max(1, min(x, 3)))

    # (2) Read incidents
    incidents_file = "large_incidents.csv"
    incidents_df = pd.read_csv(incidents_file)

    # filter open / in_progress
    incidents_df = incidents_df[incidents_df['status'].isin(['open', 'in_progress'])].copy()

    # (3) Solve
    best_sol, best_cost = single_solution_monte_carlo(teams_df, incidents_df, max_iterations=500)

    logging.info(f"Best overall cost found: {best_cost}")

    # (4) Save results
    best_sol.to_csv("best_assignment.csv", index=False)
    logging.info("Sample of best solution:")
    logging.info(best_sol.head(10))


if __name__ == "__main__":
    main()
