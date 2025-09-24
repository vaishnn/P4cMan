import json
import os
from .utils import get_app_support_directory


def load_state(file_name = "state.json"):
    '''Load state from file'''
    directory = get_app_support_directory()
    file_path = os.path.join(directory, file_name)
    data = {}
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        pass
    return data

def save_state(data, file_name = "state.json"):
    '''Save state to file'''
    directory = get_app_support_directory()
    file_path = os.path.join(directory, file_name)
    try:
        with open(file_path, 'w') as file:
            json.dump(data, file, indent=4)
    except FileNotFoundError:
        pass
