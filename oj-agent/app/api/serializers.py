def to_api_model(value):
    if isinstance(value, list):
        return [to_api_model(item) for item in value]
    if isinstance(value, dict):
        return {_camel_case(key): to_api_model(item) for key, item in value.items()}
    return value


def _camel_case(raw: str) -> str:
    if "_" not in raw:
        return raw
    head, *tail = raw.split("_")
    return head + "".join(part[:1].upper() + part[1:] for part in tail if part)
