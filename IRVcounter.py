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
