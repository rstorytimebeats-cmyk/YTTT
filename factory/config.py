import os
def env(k, d): return os.getenv(k, d)
GEN_MODEL = env("GEN_MODEL", "claude-sonnet-5-5")      # writes ideas + storyboards
JUDGE_MODEL = env("JUDGE_MODEL", "claude-opus-5-5")    # separate, stricter model rates the result
PASS_SCORE = float(env("PASS_SCORE", "8.0"))           # overall score needed (0-10)
MIN_EACH = float(env("MIN_EACH", "6.5"))               # every individual criterion must reach this
MAX_ATTEMPTS = int(env("MAX_ATTEMPTS", "4"))
PRIVACY = env("PRIVACY", "private")                    # private | unlisted | public
UPLOADER = env("UPLOADER", "none")                     # none | direct | composio
CATEGORY_ID = env("CATEGORY_ID", "27")                 # 27 = Education
STATE_PATH = env("STATE_PATH", "state/ledger.json")
OUT_DIR = env("OUT_DIR", "output")
BANNED = ["suicide", "self-harm", "self harm", "murder", "terror", "rape", "abuse", "kill yourself", "porn", "nazi", "election", "trump", "biden",
          "vaccine", "cancer cure", "diet pill", "gambling", "crypto"]
