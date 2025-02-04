"""
Contains functions needed to generate and traverse the HMM
"""

import glob
import pickle

from multiprocessing import Pool
from phoneme_decoder import *


# get the training set from the pickle file
# dictionary mapping words to lists of phonemes returned by sphinx
with open('training_set.pickle', 'rb') as handle:
    training_set = pickle.load(handle)

phonemes = {
    'pawn': ['P', 'AO', 'N'],
    'knight': ['N', 'AY', 'T'],
    'bishop': ['B', 'IH', 'SH', 'AH', 'P'],
    'rook': ['R', 'UH', 'K'],
    'queen': ['K', 'W', 'IY', 'N'],
    'king': ['K', 'IH', 'NG'],
    'takes': ['T', 'EY', 'K', 'S'],
    'castle': ['K', 'AE', 'S', 'AH', 'L'],
    '1': ['W', 'AH', 'N'],
    '2': ['T', 'UW'],
    '3': ['TH', 'R', 'IY'],
    '4': ['F', 'AO', 'R'],
    '5': ['F', 'AY', 'V'],
    '6': ['S', 'IH', 'K', 'S'],
    '7': ['S', 'EH', 'V', 'AH', 'N'],
    '8': ['EY', 'T'],
    'a': ['EY'],
    'b': ['B', 'IY'],
    'c': ['S', 'IY'],
    'd': ['D', 'IY'],
    'e': ['IY'],
    'f': ['EH', 'F'],
    'g': ['JH', 'IY'],
    'h': ['EY', 'CH'],
    'kingside': ['K', 'IH', 'NG', 'S', 'AY', 'D'],
    'queenside': ['K', 'W', 'IY', 'N', 'S', 'AY', 'D'],
    'to': ['T', 'UW'],
}

piece_names = ['king', 'queen', 'knight', 'bishop', 'rook', 'pawn']
files = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
ranks = map(str, range(1,9))
actions = ['to', 'takes', 'castle', 'kingside', 'queenside']
indices_to_words = {}
words = piece_names + files + ranks + actions



file_list = [i for i in glob.glob('wav/*') if '.wav' in i]

# Import phonemes of training sets
for w in words:
    training_set[w] = []


# For each file name
def get_phoneme_pool(filepath):
    return (filepath.split('/wav/')[1].split('_')[0], get_phonemes(filepath))


def run_pool():
    pool_party = Pool(processes=2)

    for res in pool_party.imap_unordered(get_phoneme_pool, file_list):
        training_set[res[0]].append(res[1])


for index, word in enumerate(words):
    indices_to_words[index] = (word, len(phonemes[word]))

transition_probabilities = [[0 for _ in range(27)] for _ in range(27)]

# set the transition probability of each word to itself to be n/n+1 where n is the number of
# phonemes for the word
for index in range(27):
    _, n = indices_to_words[index]
    transition_probabilities[index][index] = n * 1.0 / (n + 1)

# pieces are indices 0-5 and always transition to a file aka letter (indices 6-13)
for i in range(6):
    _, n = indices_to_words[i]
    trans_prob = 1.0 / (n + 1)
    for j in range(6, 14):
        transition_probabilities[i][j] += trans_prob * 1.0 / 8

# letters are indices 6 - 13 and always transition to numbers (indices 14-21)
for i in range(6, 14):
    _, n = indices_to_words[i]
    trans_prob = 1.0 / (n + 1)
    for j in range(14, 22):
        transition_probabilities[i][j] += trans_prob * 1.0 / 8

# numbers are indices 14-21 and transition 50% of the time to actions
# (indices 22 - 23)
for i in range(14, 22):
    _, n = indices_to_words[i]
    trans_prob = 1.0 / (n + 1)
    for j in range(14, 22):
        transition_probabilities[i][j] += trans_prob * 0.5 / 8
    for j in [22, 23]:
        transition_probabilities[i][j] += trans_prob * 0.5 / 2

# actions are indices 22-23 and always transition to letters (indices 6 - 13)
for i in [22, 23]:
    _, n = indices_to_words[i]
    trans_prob = 1.0 / (n + 1)
    for j in range(6, 14):
        transition_probabilities[i][j] += trans_prob * 1.0 / 8

# castling is index 24 and always transitions to (king/queen)side (indices 25-26)
trans_prob = 1.0 / 6
for j in [25, 26]:
    transition_probabilities[24][j] += trans_prob * 1.0 / 2

# (king/queen)side always transitions to (king/queen)side
for i in [25, 26]:
    trans_prob = 1.0 / (indices_to_words[i][1] + 1)
    transition_probabilities[i][i] += trans_prob

# get priors for pieces
priors = {}
priors['pawn'] = 8.0 / 17
for piece in ['king', 'queen', 'castle']:
    priors[piece] = 1.0 / 17
for piece in ['bishop', 'knight', 'rook']:
    priors[piece] = 2.0 / 17

# get list of phonemes
training_phonemes = set([item for sublist in training_set.values() for subsublist in sublist for item in subsublist])
actual_phonemes = set([item for sublist in phonemes.values() for item in sublist])
# actual_phonemes.add('SIL')

emission_model = {}
for phoneme in actual_phonemes:
    emission_model[phoneme] = {}
    for word in words:
        emission_model[phoneme][word] = 0.0

words = phonemes.keys()

for word, points in training_set.items():
    flattened = [item for point in points for item in point]
    total = 0
    for phoneme in actual_phonemes:
        phoneme_count = flattened.count(phoneme)
        emission_model[phoneme][word] += phoneme_count
        total += phoneme_count
    for phoneme in actual_phonemes:
        emission_model[phoneme][word] /= 1.0 * total

w_to_i = {val[0]:key for key,val in indices_to_words.iteritems()}
