# Survey app: question bank

| File | What it is |
|---|---|
| `scenes.json` | 90 scenes. **Show only `shown.context` and `shown.incoming_message`.** Never display anything under `hidden`. |
| `round_plan.json` | the item order for P1 and P2: 10 rounds of about 12 items, 115 items each |
| `post_questions.json` | the typing instructions for each register, the "I wouldn't reply" option, 3 optional questions after each answer, and the self-label picker for free-form answers |
| `free_prompts.json` | 5 "text the group" prompts |
| `profile_questions.json` | 8 questions about texting habits, asked once at the end, saved as one row per person |
| `response_schema.csv` | the output columns, one row per answer |

## Must-haves
- **Layout:** phone-friendly, chat-bubble style. Show the context line in small text and the message in a bubble, with one text box under it.
- **`{TM}`:** replace it with a teammate's first name from the app config, never the respondent's own name. Save the name used in `teammate_filled`.
- **Saving text:** save replies **exactly as typed**. Don't strip, lowercase or spellcheck. Record `seconds_to_answer`, and `edited_count` if you can.
- **"I wouldn't reply":** save the row with `abstain=true` and an empty response. Never drop it.
- **No editing** of earlier answers.
- **Save after every round**, so people can stop and pick up later. Plan two sittings of about 25 minutes.
- **`source`:** set `source=survey_v2` on every row.


## Blind version
`scenes.json` here has no `hidden` fields, so whoever builds the app can't see the labels or which scenes are held out. Leave `target_label` and `split` empty in the saved rows; we fill them in afterward by joining on `scene_id`.
