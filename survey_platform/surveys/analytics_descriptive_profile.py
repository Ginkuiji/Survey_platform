from survey_analytics import analytics_descriptive_profile as _module

globals().update({name: getattr(_module, name) for name in dir(_module) if not name.startswith("__")})
