import re


def normalize_latex(latex):
    aliases = {r"\larr": r"\leftarrow", r"\infin": r"\infty"}
    return re.sub(r"\\[a-zA-Z]+|\\.", lambda match: aliases.get(match[0], match[0]), latex).strip()
