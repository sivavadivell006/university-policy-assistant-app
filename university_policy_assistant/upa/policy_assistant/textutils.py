"""Tokenisation with light stemming - no external NLP dependencies."""
import re

STOP = set(
    "a an the is are was were be been am i me my we our you your of to in on for and or if do does did "
    "can could should would will what when where which who how whom whose it its this that these those "
    "with at by from as about into any there their they them have has had not no than then so such via "
    "per get got want need please tell us explain much many am".split()
)


def normalise(text: str) -> str:
    from .config import PHRASE_MAP

    text = text.lower()
    for pattern, repl in PHRASE_MAP:
        text = re.sub(pattern, repl, text)
    return text


def stem(w: str) -> str:
    if len(w) <= 3:
        return w
    if w.endswith("ies") and len(w) > 4:
        w = w[:-3] + "y"
    elif re.search(r"(ss|ch|sh|x|z)es$", w):
        w = w[:-2]
    elif w.endswith("s") and not w.endswith(("ss", "us")):
        w = w[:-1]
    for suf in ("ing", "ed"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            w = w[: -len(suf)]
            if len(w) >= 2 and w[-1] == w[-2] and w[-1] in "tpnmgdb":
                w = w[:-1]
            break
    if w.endswith("e") and len(w) > 4:
        w = w[:-1]
    return w


def tokenize(text: str, keep_stop: bool = False) -> list[str]:
    toks = re.findall(r"[a-z0-9]+", normalise(text))
    return [stem(t) for t in toks if keep_stop or t not in STOP]
