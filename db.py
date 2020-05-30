import os, json

DB = "db.json"

def load_db() -> set:
    """ Loads the json file. """
    if os.path.exists(DB):
        with open(DB) as f:
            return set(json.load(f))
    return set()

def save_db(data: set) -> None:
    """ Stores an updated version to the database. """
    with open(DB, "w") as f:
        json.dump(list(data), f)
