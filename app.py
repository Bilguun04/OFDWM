import pandas as pd
import random
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed

logging.basicConfig(level=logging.INFO, format='%(message)s')
MISS_CASE_PENALTY = 1000
NO_UNITS_PENALTY = 400
OVER_ASSIGN_PENALTY = 200
HIGH_POWER_LOW_SEVERITY = 300
LEFTOVER_UNITS_WEIGHT = 10.0

def generate_initial_solution(teams_df, incidents_df):

    assignment_df = incidents_df.copy()
    assignment_df['assigned_team'] = None


    team_units_left = dict(zip(teams_df['team_name'], teams_df['units_available']))

    team_crimes = {
        row['team_name']: set(str(row['crime_types']).split(';')) for _, row in teams_df.iterrows()
    }

    for idx, inc in assignment_df.iterrows():
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
            assignment_df.at[idx, 'assigned_team'] = None

    return assignment_df


def evaluate_solution(teams_df, incidents_df, assignment_df):

    team_power = dict(zip(teams_df['team_name'], teams_df['power']))
    team_crimes = {}
    for idx, row in teams_df.iterrows():
        team_crimes[row['team_name']] = set(str(row['crime_types']).split(';'))

    team_avail = dict(zip(teams_df['team_name'], teams_df['units_available']))

    used_units = {t: 0 for t in teams_df['team_name']}

    total_penalty = 0.0

    for idx, inc_row in assignment_df.iterrows():
        severity = inc_row['severity']
        crime_type = inc_row['crime_type']
        assigned_team = inc_row['assigned_team']

        if assigned_team is None:
            total_penalty += MISS_CASE_PENALTY
            continue


        row_team = teams_df[teams_df['team_name'] == assigned_team]
        if row_team.empty:
            total_penalty += MISS_CASE_PENALTY
            continue

        used_units[assigned_team] += 1

        power = team_power[assigned_team]


        if power > severity:
            total_penalty += OVER_ASSIGN_PENALTY

        if severity <= 2 and power >= 5:
            total_penalty += HIGH_POWER_LOW_SEVERITY


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


def refine_solution(teams_df, incidents_df, assignment_df, max_iterations=100):

    best_df = assignment_df.copy()
    best_pen = evaluate_solution(teams_df, incidents_df, best_df)

    for _ in range(max_iterations):
        new_df = best_df.copy().reset_index(drop=True)


        if len(new_df) == 0:
            break
        inc_idx = random.randint(0, len(new_df) - 1)
        crime_type = new_df.loc[inc_idx, 'crime_type']


        usage = {t: 0 for t in teams_df['team_name']}
        for i, row in new_df.iterrows():
            if row['assigned_team'] in usage and row['assigned_team'] is not None:
                usage[row['assigned_team']] += 1


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



def single_monte_carlo_run(seed, teams_df, incidents_df, refine_iters=200):

    random.seed(seed)


    init_sol = generate_initial_solution(teams_df, incidents_df)

    refined = refine_solution(teams_df, incidents_df, init_sol, max_iterations=refine_iters)

    penalty = evaluate_solution(teams_df, incidents_df, refined)
    return (refined, penalty)


def parallel_monte_carlo(teams_df, incidents_df, num_runs=10, refine_iters=200):

    best_sol = None
    best_pen = float('inf')


    seeds = [random.randint(0, 1_000_000_000) for _ in range(num_runs)]


    with ProcessPoolExecutor() as executor:

        futures = []
        for s in seeds:
            futures.append(
                executor.submit(single_monte_carlo_run, s, teams_df, incidents_df, refine_iters)
            )

        for future in as_completed(futures):
            sol, pen = future.result()
            if pen < best_pen:
                best_pen = pen
                best_sol = sol

    return best_sol, best_pen



def main():

    teams_df = pd.read_csv("large_teams.csv")
    incidents_df = pd.read_csv("large_incidents.csv")


    incidents_df = incidents_df[incidents_df['status'].isin(['open', 'in_progress'])].copy()


    best_solution_df, best_cost = parallel_monte_carlo(
        teams_df,
        incidents_df,
        num_runs=20,
        refine_iters=300
    )

    logging.info(f"Best cost found across all parallel runs: {best_cost}")


    best_solution_df.to_csv("best_assignment_parallel.csv", index=False)
    logging.info("Sample of best solution:")
    logging.info(best_solution_df.head(10))


if __name__ == "__main__":
    main()
