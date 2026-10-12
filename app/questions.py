"""Questionnaire content for the Lexicon Personality Bot.

Edit the lists below to change what the questionnaire asks. The app in
questionnaire.py reads them; no other code needs to change.
"""

# Section 1: multiple-choice questions about how you usually write.
# "key" is the field name saved in the JSON answers file.
STYLE_QUESTIONS = [
    {
        "key": "text_length",
        "label": "How long are your text messages usually?",
        "options": ["A few words", "One or two sentences", "A short paragraph", "Longer than a paragraph"],
    },
    {
        "key": "tone",
        "label": "Which best describes your writing tone?",
        "options": ["Direct and to the point", "Warm and friendly", "Detailed and thorough", "Funny or playful"],
    },
    {
        "key": "emoji_use",
        "label": "How often do you use emojis?",
        "options": ["Never", "Sometimes", "Often"],
    },
    {
        "key": "exclamation_use",
        "label": "How often do you use exclamation points?",
        "options": ["Rarely", "Sometimes", "A lot!"],
    },
    {
        "key": "capitalization",
        "label": "How do you capitalize in casual texts?",
        "options": ["Proper capitalization", "Mostly lowercase", "It depends"],
    },
    {
        "key": "email_greeting",
        "label": "How do you usually start an email?",
        "options": ["Hi [name],", "Hey [name],", "Hello [name],", "Dear [name],", "No greeting"],
    },
    {
        "key": "email_signoff",
        "label": "How do you usually end an email?",
        "options": ["Thanks,", "Best,", "Cheers,", "Regards,", "No sign-off"],
    },
    {
        "key": "structure",
        "label": "When you explain something, you usually write...",
        "options": ["Short bullet points", "Numbered steps", "Paragraphs"],
    },
]

# A 1 to 5 slider question.
FORMALITY_LABELS = {1: "Very casual", 2: "Casual", 3: "In between", 4: "Formal", 5: "Very formal"}

# Section 2: short scenario replies. Same prompts for everyone, so we can
# compare how different people answer the same message.
SCENARIOS = [
    {
        "key": "scheduling",
        "title": "Scheduling",
        "prompt": "\"Can we move our meeting to Thursday?\" Assume Thursday works and you want to suggest 2 p.m.",
    },
    {
        "key": "thank_you",
        "title": "Thank-you",
        "prompt": "Someone helped you debug your notebook. How would you thank them?",
    },
    {
        "key": "polite_refusal",
        "title": "Polite refusal",
        "prompt": "\"Can you help with the presentation this weekend?\" Assume you're unavailable.",
    },
    {
        "key": "clarification",
        "title": "Asking for clarification",
        "prompt": "\"Can you update your section?\" Ask which section and what changes are needed.",
    },
    {
        "key": "apology",
        "title": "Apologizing",
        "prompt": "\"We waited for you at the meeting.\" Assume you forgot the meeting. Apologize and ask what you missed.",
    },
    {
        "key": "progress_update",
        "title": "Progress update",
        "prompt": "\"How's your part of the project going?\" Assume your draft is finished, testing remains, and you expect to finish tomorrow.",
    },
    {
        "key": "reminder",
        "title": "Sending a reminder",
        "prompt": "Your teammate said, \"I'll send you my slides later.\" It's now the next day. Remind them that you need the slides by 6 p.m.",
    },
    {
        "key": "offering_help",
        "title": "Offering help",
        "prompt": "\"I'm stuck getting the demo to run.\" Assume you have 30 minutes available tonight to help troubleshoot.",
    },
    {
        "key": "disagreeing",
        "title": "Disagreeing respectfully",
        "prompt": "\"Let's skip testing and just present the demo.\" Explain that you think one quick test is necessary before presenting.",
    },
    {
        "key": "encouragement",
        "title": "Giving encouragement",
        "prompt": "\"My generated results aren't very good.\" Encourage them and suggest reviewing the results together.",
    },
]

# Minimum number of scenario replies needed to submit.
MIN_SCENARIO_REPLIES = 3
