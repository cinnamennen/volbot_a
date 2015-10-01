import random

responses = {
    "join": [
        "Hello!",
    ],

    "quit": [
        "Goodbye!",
        "bye.",
        "adios.",
    ],

    "access_denied": [
        "No way!",
        ":/",
        "ACCESS DENIED",
    ],

    "unknown_command": [
        "what?",
        "unknown command.",
    ],

    "internal_error": [
        "Oops, internal error.",
    ],
}

def get_resp(name):
    return random.choice(responses[name])
