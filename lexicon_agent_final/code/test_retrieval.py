"""Smoke test for lexicon_retrieval (uses a throwaway exclude list, NOT the frozen split)."""
from lexicon_retrieval import ExampleStore
store = ExampleStore.from_survey("../data/p1_survey.csv", "../prompt_bank_v2.csv",
                                 exclude_scene_ids={"L17_1", "L17_2"})
df = store.df
assert not df.scene_id.isin({"L17_1", "L17_2"}).any(), "excluded scene leaked"
assert (df.register == "chat").all() and (df.response.str.len() > 0).all()
assert df.user_id.eq("P1").all()
print("rows in store:", len(df))
q = "can you also cover the demo tomorrow? I'm buried"
for c in ("A_plain", "B_semantic", "C_context", "E_styledistance"):
    refs = store.retrieve(c, "P1", "Phil: " + q, k=3, label="Push Back on Request",
                          intended_meaning="I can't, I'm busy too")
    print(c, [(r.incoming[:40], r.reply) for r in refs])
print("P2 isolation:", store.retrieve("B_semantic", "P2", q))
print("style sim (P1-ish vs formal):",
      [round(x, 3) for x in store.style_similarity("P1", ["Nope, not today ", "Dear colleague, I regret to inform you that I am unavailable."])])
print("OK")
