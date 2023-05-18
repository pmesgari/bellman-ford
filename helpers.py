from os import listdir
from os.path import isfile, join


def get_files(folder):
    return [f for f in listdir(folder) if isfile(join(folder, f))]


def load(file):
    """Load the solution file and return a dictionary of distance vectors for each node"""
    with open(file) as f:
        lines = f.read().splitlines()
    
    lines = [l.replace(' ', '') for l in lines]
    
    result = {}
    for line in lines:
        node, dv = line.split(':')
        result[node] = dv
    
    return result