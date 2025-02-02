import pandas as pd
import numpy as np
import random
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed

logging.basicConfig(level=logging.INFO, format='%(message)s')


def generate_initial_solution(teams_df, incidents_df):
    """
    Example placeholder: fill in your actual approach to build an initial assignment.
    Returns a DataFrame (or dict) representing the assignment (e.g., incidents_df with 'assigned_team' column).
    """
    assignment_df = incidents_df.copy()
    assignment_df['assigned_team'] = None

    # [Insert your logic, e.g. sorting by severity or random assignment...]
    # For demonstration, we'll just randomly assign feasible teams or None
    team_units_left = dict(zip(teams_df['team_name'], teams_df['units_available']))

    # Convert string crime_types to sets
    team_crimes = {
        row['team_name']: set(str(row['crime_types']).split(';')) for _, row in teams_df.iterrows()
    }

    for idx, inc in assignment_df.iterrows():
        # find feasible
        feas_teams = []
        for _, trow in teams_df.iterrows():
            tname = trow['team_name']
            if inc['crime_type'] in team_crimes[tname] and team_units_left[tname] > 0:
                feas_teams.append(tname)

        if feas_teams:
            chosen = random.choice(feas_teams)
            assignment_df.at[idx, 'assigned_team'] = chosen
            team_units_left[chosen] -= 1
        else:
            # None => big penalty later
            assignment_df.at[idx, 'assigned_team'] = None

    return assignment_df


def evaluate_solution(teams_df, incidents_df, assignment_df):
    """
    Example placeholder: compute the total penalty of 'assignment_df'.
    Return a float (lower = better).
    """
    total_penalty = 0.0

    # Build quick lookups
    team_power = dict(zip(teams_df['team_name'], teams_df['power']))
    team_crimes = {
        row['team_name']: set(str(row['crime_types']).split(';')) for _, row in teams_df.iterrows()
    }

    # For each incident, see if assigned, if feasible, etc.
    for idx, inc in assignment_df.iterrows():
        at = inc['assigned_team']
        if at is None:
            total_penalty += 9999  # huge penalty for unassigned
        else:
            # check coverage
            if inc['crime_type'] not in team_crimes[at]:
                total_penalty += 9999
            else:
                # penalty = max(0, severity - power)
                sev = inc['severity']
                power = team_power[at]
                total_penalty += max(0, sev - power)

    return total_penalty


def refine_solution(teams_df, incidents_df, assignment_df, max_iterations=100):
    """
    Example placeholder: local search to reduce penalty by random reassignments.
    Return an improved assignment_df.
    """
    best_df = assignment_df.copy()
    best_pen = evaluate_solution(teams_df, incidents_df, best_df)

    for _ in range(max_iterations):
        new_df = best_df.copy().reset_index(drop=True)

        # pick random incident to reassign
        if len(new_df) == 0:
            break
        inc_idx = random.randint(0, len(new_df) - 1)
        crime_type = new_df.loc[inc_idx, 'crime_type']

        # Recompute usage
        usage = {t: 0 for t in teams_df['team_name']}
        for i, row in new_df.iterrows():
            if row['assigned_team'] in usage and row['assigned_team'] is not None:
                usage[row['assigned_team']] += 1

        # feasible teams
        feas_teams = []
        for _, trow in teams_df.iterrows():
            tname = trow['team_name']
            cset = set(str(trow['crime_types']).split(';'))
            if crime_type in cset and usage[tname] < trow['units_available']:
                feas_teams.append(tname)

        if not feas_teams:
            continue

        chosen_team = random.choice(feas_teams)
        new_df.loc[inc_idx, 'assigned_team'] = chosen_team

        new_pen = evaluate_solution(teams_df, incidents_df, new_df)
        if new_pen < best_pen:
            best_df = new_df.copy()
            best_pen = new_pen

    return best_df


# -------------------------------------------------------------------------
#               PARALLEL MONTE CARLO APPROACH
# -------------------------------------------------------------------------

def single_monte_carlo_run(seed, teams_df, incidents_df, refine_iters=200):
    """
    Run one random start + refinement, given a random seed.
    Return (assignment_df, penalty).
    """
    # Each process can set its own random seed so there's no overlap
    random.seed(seed)

    # 1) generate
    init_sol = generate_initial_solution(teams_df, incidents_df)
    # 2) refine
    refined = refine_solution(teams_df, incidents_df, init_sol, max_iterations=refine_iters)
    # 3) evaluate
    penalty = evaluate_solution(teams_df, incidents_df, refined)
    return (refined, penalty)


def parallel_monte_carlo(teams_df, incidents_df, num_runs=10, refine_iters=200):
    """
    Launch multiple parallel runs using concurrent.futures.ProcessPoolExecutor.
    Each run is a separate random seed, so we get diverse solutions.
    """
    best_sol = None
    best_pen = float('inf')

    # Generate random seeds
    seeds = [random.randint(0, 1_000_000_000) for _ in range(num_runs)]

    # We'll pass teams_df and incidents_df as read-only data:
    # But be mindful: large DataFrames can get pickled for each process,
    # so you might want to reduce or only pass minimal data if needed.

    with ProcessPoolExecutor() as executor:
        # submit tasks
        futures = []
        for s in seeds:
            futures.append(
                executor.submit(single_monte_carlo_run, s, teams_df, incidents_df, refine_iters)
            )
        # collect results
        for future in as_completed(futures):
            sol, pen = future.result()
            if pen < best_pen:
                best_pen = pen
                best_sol = sol

    return best_sol, best_pen


# -------------------------------------------------------------------------
#               MAIN SCRIPT
# -------------------------------------------------------------------------

def main():
    # 1) read input
    teams_df = pd.read_csv("large_teams.csv")
    incidents_df = pd.read_csv("large_incidents.csv")

    # filter to open / in_progress
    incidents_df = incidents_df[incidents_df['status'].isin(['open', 'in_progress'])].copy()

    # 2) run parallel Monte Carlo
    best_solution_df, best_cost = parallel_monte_carlo(
        teams_df,
        incidents_df,
        num_runs=20,  # how many parallel runs
        refine_iters=300  # how many local-search iterations per run
    )

    logging.info(f"Best cost found across all parallel runs: {best_cost}")

    # 3) save or inspect best solution
    best_solution_df.to_csv("best_assignment_parallel.csv", index=False)
    logging.info("Sample of best solution:")
    logging.info(best_solution_df.head(10))


if __name__ == "__main__":
    main()
