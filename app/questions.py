"""Questionnaire content for the Lexicon Personality Bot.

Each question pairs one LABEL (how to reply) with a random CONTEXT (what you
are replying to). Edit the lists below to change the questionnaire; the app in
questionnaire.py reads them and no other code needs to change.
"""

# Reply types. "[topic]" is replaced with the context's topic.
LABELS = [
    {"label": "Full Agree", "template": "Agree with this idea about [topic]."},
    {"label": "Full Disagree", "template": "Disagree with this idea about [topic]."},
    {"label": "Partial Agree + Modification", "template": "Agree with the idea about [topic], but suggest a small change."},
    {"label": "5W1H Question", "template": "Ask a what / where / when / how / why question about [topic]."},
    {"label": "Reverify / Confirm", "template": "Check or confirm something about [topic]."},
    {"label": "Suggest / Propose", "template": "Suggest an alternative or different plan for [topic]."},
    {"label": "Elaborate / Expand", "template": "Add more detail or explanation about [topic]."},
    {"label": "Soften / Hedge", "template": "Respond about [topic] in a polite or softer way."},
    {"label": "Direct / Blunt", "template": "Respond about [topic] in a short and direct way."},
    {"label": "Acknowledge", "template": "Give a short acknowledgment about [topic]."},
    {"label": "Correct / Restate", "template": "Correct or rephrase something about [topic]."},
    {"label": "Refuse / Decline", "template": "Decline or say no to something about [topic]."},
    {"label": "Summarize / Condense", "template": "Summarize the idea about [topic] more briefly."},
    {"label": "Express Emotion", "template": "Respond about [topic] while showing how you feel (happy, annoyed, excited, etc.)."},
]

# Everyday situations. "message" is what someone says to you; "topic" fills
# [topic] in the label's template.
CONTEXTS = [
    {
        "name": "Restaurant",
        "topic": "dinner at the new ramen place",
        "message": "Hey, want to try the new ramen place downtown Friday at 7? I heard it's really good.",
    },
    {
        "name": "Movies",
        "topic": "the movie night plan",
        "message": "Let's catch the 9:30 showing of the new sci-fi movie on Saturday. I can buy the tickets.",
    },
    {
        "name": "Library",
        "topic": "studying at the library",
        "message": "Want to study at the library tomorrow from 2 to 6? I booked a room on the third floor.",
    },
    {
        "name": "Group project",
        "topic": "the group project plan",
        "message": "I think we should split the project into five parts and finish our drafts by Sunday night.",
    },
    {
        "name": "Gym",
        "topic": "the morning workout plan",
        "message": "Let's start going to the gym at 6 a.m. on Mondays and Wednesdays.",
    },
    {
        "name": "Coffee shop",
        "topic": "meeting at the coffee shop",
        "message": "Can we meet at the coffee shop near campus at 10 tomorrow to go over the slides?",
    },
    {
        "name": "Road trip",
        "topic": "the weekend road trip",
        "message": "Road trip to Santa Cruz this Saturday? We'd leave at 8 a.m. and I'll drive.",
    },
    {
        "name": "Concert",
        "topic": "the concert tickets",
        "message": "Tickets for the concert next month are $85 each. Should we get them before they sell out?",
    },
    {
        "name": "Birthday party",
        "topic": "the surprise birthday party",
        "message": "Let's throw a surprise party for Sam at my place next Friday. Everyone brings a dish.",
    },
    {
        "name": "Exam study session",
        "topic": "the exam study session",
        "message": "The midterm is Tuesday. Want to do a study session Sunday night over video call?",
    },
]
