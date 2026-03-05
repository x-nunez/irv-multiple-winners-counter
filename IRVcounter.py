#!/usr/bin/env python3

import argparse as ap
import pandas as pd
import random as r
import os

VERBOSE = False

def count_first_choice_votes(candidates: list, ballots: list[list]) -> dict:
	"""
	Count first-choice votes for current candidates
	Args:
		candidates (list): A list of candidates
		ballots (list[list]): A list of ballots, where each ballot is a list of ranked candidates
	Returns:
		dict: Mapping candidate -> first-choice votes
	"""
	votes = {c: 0 for c in candidates}

	for b in ballots:
		votes[b[0]] += 1

	return votes

def restricted_recount_tiebreak(tied: list, ballots: list[list]) -> list:
	"""
	Perform a restricted pairwise recount among tied candidates.
	For each ballot, find the highest-ranked candidate among `tied` and
	give them one vote. Return the candidate(s) with the fewest votes.
	Args:
		tied (list): The candidates tied for elimination
		ballots (list[list]): The current ballots (full rankings)
	Returns:
		list: The candidate(s) with the lowest restricted recount total
	"""
	votes = {c: 0 for c in tied}

	for b in ballots:
		for candidate in b:
			if candidate in votes:
				votes[candidate] += 1
				break # The first match is the highest-ranked

	min_votes = min(votes.values())
	return [c for c in tied if votes[c] == min_votes]

def retrospective_round_tiebreak(tied: list, previous_round_votes: list[dict]):
	"""
	Find the most recent prior round where tied candidates are not tied at the
	lowest vote total, then eliminate the unique lowest candidate in that round
	Args:
		tied (list): The candidates tied for elimination
		previous_round_votes (list[dict]): Vote history, excluding current round
	Returns:
		list: A list with single candidate to eliminate, or [] when unresolved
	"""
	for round_votes in reversed(previous_round_votes):
		min_votes = min([round_votes[c] for c in tied])

		lowest = [c for c in tied if round_votes[c] == min_votes]

		if len(lowest) < len(tied):
			return lowest

	return []

def eliminate_less_voted(candidates: list, ballots: list[list], less_voted: list):
	"""
	Eliminate the less voted candidate(s) from candidates list and ballots
	Args:
		candidates (list): A list of candidates
		ballots (list[list]): A list of ballots, where each ballot is a list of ranked candidates
		less_voted (list): A list of less voted candidate(s)
	"""
	for c in less_voted:
		candidates.remove(c)

		for b in ballots:
			if c in b:
				b.remove(c)

	while [] in ballots:
		ballots.remove([])

def counter(candidates: list, ballots: list[list], n: int):
	"""
	Determine winners using Instant Runoff Voting
	Args:
		candidates (list): A list of candidates
		ballots (list[list]): A list of ballots, where each ballot is a list of ranked candidates
		n (int): The number of candidates to select
	"""
	candidates_left = candidates.copy()
	ballots_left = [b.copy() for b in ballots]

	current_round = 0
	round_vote_history = []
	while (len(candidates_left) > n):
		current_round += 1
		if VERBOSE:
			print(f"Round {current_round}:")

		current_votes = count_first_choice_votes(candidates_left, ballots_left)
		round_vote_history.append(current_votes.copy())

		min_votes = min(current_votes.values())
		less_voted = [c for c in candidates_left if current_votes[c] == min_votes]

		tie = len(candidates_left) - len(less_voted) < n

		if tie:
			recount_less_voted = restricted_recount_tiebreak(less_voted, ballots_left)
			if VERBOSE:
				print(f"\tTie among {less_voted}")

			if len(recount_less_voted) < len(less_voted):
				less_voted = recount_less_voted
				tie = len(candidates_left) - len(less_voted) < n

			if tie:
				retrospective_less_voted = retrospective_round_tiebreak(less_voted, round_vote_history[:-1])
				while (retrospective_less_voted != [] and len(candidates_left) - len(retrospective_less_voted) < n):
					retrospective_less_voted = retrospective_round_tiebreak(retrospective_less_voted, round_vote_history[:-1])

				if retrospective_less_voted:
					less_voted = retrospective_less_voted
					tie = len(candidates_left) - len(less_voted) < n
					if VERBOSE:
						print(f"\t\tretrospective tie-break selects for elimination: {retrospective_less_voted}")

				elif VERBOSE:
					print(f"\t\tUnable to resolve tie, random selection required")

			elif VERBOSE:
				print(f"\t\trestricted recount selects for elimination: {recount_less_voted}")

		eliminate_less_voted(candidates_left, ballots_left, less_voted)

		if VERBOSE and tie:
			print(f"\tRemains: {candidates_left}, tied {less_voted}, random tie-break proposal: {r.sample(less_voted, n - len(candidates_left))}")
		elif VERBOSE:
			print(f"\tRemains: {candidates_left}, eliminated: {less_voted}")
		elif tie:
			print(f"Tied candidates: {less_voted}, random tie-break proposal: {r.sample(less_voted, n - len(candidates_left))}")

	print(f"Winner(s): {candidates_left}")

def check_ballot(ballot: list) -> tuple:
	"""
	Check if a ballot is valid, blank, or null.
	A ballot is valid if:
		- It has no candidates marked (blank), or
		- The k marked candidates have rankings exactly {1, 2, ..., k}
	Args:
		ballot (list): A list of ranked candidates
	Returns:
		tuple: (cleaned_ballot, status) where cleaned_ballot has empty strings
			removed and status is 'valid', 'blank', or 'null'
	"""
	aux = []
	blank = False
	semiblank = False
	for c in ballot:
		if blank or semiblank:
			if c != '':
				return ballot, 'null'
		elif c == '':
			if len(aux) == 0:
				blank = True
			else:
				semiblank = True
		elif c not in aux:
			aux.append(c)
		else:
			return ballot, 'null'

	ballot = [c for c in ballot if c != '']

	if blank:
		return ballot, 'blank'
	return ballot, 'valid'

def main():
	global VERBOSE
	parser = ap.ArgumentParser()
	parser.add_argument("inputfile", help="Path to the results (CSV)")
	parser.add_argument("-v", "--verbose", action="store_true", help="Shows the counting process")
	parser.add_argument("-w", "--winners", type=int, default=1, help="Number of eligible candidates (default: 1)")
	args = parser.parse_args()
	VERBOSE = args.verbose

	if args.winners <= 0:
		print("Error: Number of winners must be greater than 0")
		return

	print("▗▄▄▄▖▗▄▄▖ ▗▖  ▗▖     ▗▄▄▖ ▗▄▖ ▗▖ ▗▖▗▖  ▗▖▗▄▄▄▖▗▄▄▄▖▗▄▄▖ ")
	print("  █  ▐▌ ▐▌▐▌  ▐▌    ▐▌   ▐▌ ▐▌▐▌ ▐▌▐▛▚▖▐▌  █  ▐▌   ▐▌ ▐▌")
	print("  █  ▐▛▀▚▖▐▌  ▐▌    ▐▌   ▐▌ ▐▌▐▌ ▐▌▐▌ ▝▜▌  █  ▐▛▀▀▘▐▛▀▚▖")
	print("▗▄█▄▖▐▌ ▐▌ ▝▚▞▘     ▝▚▄▄▖▝▚▄▞▘▝▚▄▞▘▐▌  ▐▌  █  ▐▙▄▄▖▐▌ ▐▌")
	print("                                IRV counter tool by Xian\n")

	if not os.path.exists(args.inputfile):
		print(f"Error: {args.inputfile} is not a valid input")
		return

	csv = pd.read_csv(args.inputfile, header=None, sep=';', dtype=str, keep_default_na=False)

	valid_ballots = []
	blank_ballots = []
	null_ballots = []
	for _, row in csv.iterrows():
		ballot = row.tolist()
		ballot, ballot_type = check_ballot(ballot)
		if ballot_type == 'valid':
			valid_ballots.append(ballot)
		elif ballot_type == 'blank':
			blank_ballots.append(ballot)
		else:
			null_ballots.append(ballot)

	candidates = []
	for b in valid_ballots:
		for c in b:
			if c not in candidates:
				candidates.append(c)

	if VERBOSE:
		print(f"{len(valid_ballots)} valid ballots")
	if VERBOSE:
		print(f"{len(blank_ballots)} blank ballots")
	if VERBOSE:
		print(f"{len(null_ballots)} null ballots:")
		for b in null_ballots:
			print(f"\t{b}")
	if VERBOSE:
		print(f"\nCandidates: {candidates}")

	if args.winners >= len(candidates):
		print(f"Requested {args.winners} winners but only {len(candidates)} candidates. All are winners.")
	else:
		counter(candidates, valid_ballots, args.winners)

if __name__ == "__main__":
	main()
