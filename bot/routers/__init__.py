from .birthday import birthday_router
from .development import development_router
from .general import general_router

routers = [general_router, development_router, birthday_router]
