import tomllib
from pathlib import Path


def load(path="agent.toml"):
    source = Path(path).resolve()
    with source.open("rb") as stream:
        config = tomllib.load(stream)
    config["base"] = str(source.parent)
    for key in ("workspace", "state"):
        target = (source.parent / config["paths"][key]).resolve()
        target.mkdir(parents=True, exist_ok=True)
        config["paths"][key] = str(target)
    return config
