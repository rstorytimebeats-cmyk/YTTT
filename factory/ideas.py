from . import config, llm, prompts

def refill(ledger, n=20):
    past = [q["topic"] for q in ledger["queue"]] + [v.get("topic", "") for v in ledger["videos"]]
    r = llm.ask_json("ideas", config.GEN_MODEL, prompts.IDEA_SYSTEM, f"Give {n} NEW ideas. Do not repeat or closely resemble any of these:\n" + "\n".join(past[-120:]), max_tokens=3000)
    for i in r.get("ideas", []):
        t = i.get("topic", "").strip()
        if t and not any(w in t.lower() for w in config.BANNED) and t not in past:
            ledger["queue"].append({"topic": t, "category": i.get("category", ""), "fact_hook": i.get("fact_hook", ""), "status": "planned"})

def pick(ledger):
    if not any(q["status"] == "planned" for q in ledger["queue"]): refill(ledger)
    for q in ledger["queue"]:
        if q["status"] == "planned": return q
    raise RuntimeError("no ideas available")
