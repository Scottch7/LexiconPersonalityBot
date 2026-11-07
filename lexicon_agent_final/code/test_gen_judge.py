import pandas as pd
from types import SimpleNamespace as NS
from lexicon_gen_judge import *

class Fake:
    def __init__(self, outs): self.outs=list(outs); self.chat=NS(completions=NS(create=self.create)); self.calls=[]
    def create(self, **kw):
        self.calls.append(kw); o=self.outs.pop(0)
        return NS(choices=[NS(message=NS(content=o))], usage=NS(total_tokens=10))

d = pd.read_csv("/home/box/agent-data/agents/58b6dfbd-bd4a-4e83-87e4-ac1a384e1591/attachments/29e10084ac0a06ef76c678e84031de81f13b0b9752089e064cc557f39135e5ce.csv")
card = build_style_card(d[d.register=="chat"].response.dropna().tolist())
print(card)
refs=[Ref("party friday?","Yup, I m in","accept","friend","low")]
c=Fake(['"Yup, I m in for it"', "Sure, I can do it"])
r=generate_reply(c,"P1","agrees to go","movie saturday?",style_card=card,refs=refs)
assert r.attempts==2 and r.reply=="Sure, I can do it", r
assert c.calls[0]["max_tokens"]==30
c=Fake(['{"winner":"A"}','{"winner":"B"}']); assert judge_style_pair(c,"Is it ?",["Good Job"],"real","plain")=="x"
c=Fake(['{"winner":"A"}','{"winner":"A"}']); assert judge_style_pair(c,"r",[],"a","b")=="tie"
c=Fake(['{"score":4,"act_matches":true,"added_facts":false}']); assert judge_meaning(c,"m","i","c")["score"]==4
assert gist_ok("agrees to attend","Yup, I m in") and not gist_ok("yup i m in now","Yup, I m in now ok")
print(bootstrap_ci(["x"]*30+["y"]*5+["tie"]*5))
print("all tests passed")
