from . import common as _common
from . import visibility as _visibility
from . import question_types as _question_types
from . import summary as _summary

for _module in (_common, _visibility, _question_types, _summary):
    globals().update({name: getattr(_module, name) for name in dir(_module) if not name.startswith("__")})


def classify_question_response_state(*args, **kwargs):
    _visibility._response_seen_question_ids = globals().get(
        "_response_seen_question_ids",
        _visibility._response_seen_question_ids,
    )
    return _visibility.classify_question_response_state(*args, **kwargs)
