"""Settings for questionnaire v2.

TEAMMATE_NAMES fill the {TM} placeholder in scene messages ("{TM}: omw, 10 min late").
To change them without editing code, add them to Streamlit secrets
(.streamlit/secrets.toml locally, or the app's Secrets box on Streamlit Cloud):

    teammate_names = ["Name1", "Name2"]
"""

TEAMMATE_NAMES = ["Phil", "Zach"]

# Who each participant is, only so nobody sees their own name in a message.
PARTICIPANT_NAMES = {"P1": "Kevin", "P2": "Zach"}

# The 5 negative scenes Phil picked for the pilot run before the full survey.
PILOT_SCENES = ["L04_1", "L05_1", "L15_1", "L17_1", "L19_1"]

# Required break at the halfway point: after this round, wait this many minutes
# before the next one (also checked when resuming from a CSV). Set minutes to 0 to only suggest it.
BREAK_AFTER_ROUND = 5
BREAK_MINUTES = 10

# A "proper" reply shorter than this many words gets one nudge to write more.
PROPER_MIN_WORDS = 4

SOURCE = "survey_v2"
ORIGIN = "survey"
