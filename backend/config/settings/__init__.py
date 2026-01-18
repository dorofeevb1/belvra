from .base import *

from environs import Env

env = Env()
env.read_env()

ENVIRONMENT = env.str("DJANGO_ENV", default="development")

if ENVIRONMENT == "production":
    from .production import *
elif ENVIRONMENT == "staging":
    from .staging import *
else:
    from .development import *
