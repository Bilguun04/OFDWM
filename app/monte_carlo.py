import pandas as pd
import random
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed

logging.basicConfig(level=logging.INFO, format="%(message)s")

MISS_CASE_PENALTY = 1000
NO_UNITS_PENALTY = 400
OVER_ASSIGN_PENALTY = 200
HIGH_POWER_LOW_SEVERITY = 300
LEFTOVER_UNITS_WEIGHT = 10.0


def generate_initial_solution(teams_df, incidents_df):
    """Assigns teams to incidents randomly."""
    assignment_df = incidents_df.copy()
    assignment_df["assigned_team"] = None

    team_units_left = dict(zip(teams_df["team_name"], teams_df["units_available"]))
    team_crimes = {row["team_name"]: set(str(row["crime_types"]).split(";")) for _, row in teams_df.iterrows()}

    for idx, inc in assignment_df.iterrows():
        feas_teams = [tname for tname in team_crimes if inc["crime_type"] in team_crimes[tname] and team_units_left[tname] > 0]

        if feas_teams:
            chosen = random.choice(feas_teams)
            assignment_df.at[idx, "assigned_team"] = chosen
            team_units_left[chosen] -= 1

    return assignment_df


def evaluate_solution(teams_df, assignment_df):
    """Calculates total penalty of the assignment."""
    total_penalty = 0.0
    team_power = dict(zip(teams_df["team_name"], teams_df["power"]))

    for _, row in assignment_df.iterrows():
        assigned_team = row["assigned_team"]
        severity = row["severity"]

        if assigned_team is None:
            total_penalty += MISS_CASE_PENALTY
        else:
            power = team_power.get(assigned_team, 0)
            if power > severity:
                total_penalty += OVER_ASSIGN_PENALTY

    return total_penalty


def refine_solution(teams_df, assignment_df, max_iterations=100):
    """Refines the solution to reduce penalties."""
    best_df = assignment_df.copy()
    best_penalty = evaluate_solution(teams_df, best_df)

    for _ in range(max_iterations):
        new_df = best_df.copy()
        random_idx = random.randint(0, len(new_df) - 1)
        new_df.at[random_idx, "assigned_team"] = None
        new_penalty = evaluate_solution(teams_df, new_df)

        if new_penalty < best_penalty:
            best_df = new_df.copy()
            best_penalty = new_penalty

    return best_df


def single_monte_carlo_run(seed, teams_df, incidents_df, refine_iters):
    """Runs a single iteration of the Monte Carlo method."""
    random.seed(seed)
    initial_solution = generate_initial_solution(teams_df, incidents_df)
    refined_solution = refine_solution(teams_df, initial_solution, refine_iters)
    penalty = evaluate_solution(teams_df, refined_solution)
    return refined_solution, penalty


def parallel_monte_carlo(teams_df, incidents_df, num_runs=10, refine_iters=100):
    """Runs multiple Monte Carlo simulations in parallel."""
    best_solution = None
    best_penalty = float("inf")

    with ProcessPoolExecutor() as executor:
        futures = {executor.submit(single_monte_carlo_run, random.randint(0, 10**6), teams_df, incidents_df, refine_iters): i for i in range(num_runs)}

        for future in as_completed(futures):
            solution, penalty = future.result()
            if penalty < best_penalty:
                best_penalty = penalty
                best_solution = solution

    return best_solution, best_penalty
