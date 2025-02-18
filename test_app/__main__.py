from starlette.applications import Starlette
from starlette.routing import Mount

from test_app.app import app as gql_app

app = Starlette(
    routes=[
        Mount("/graphql", gql_app),
    ]
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "test_app.__main__:app",
        reload=True,
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "rich": {
                    "datefmt": "[%X]",
                    "format": "%(message)s",
                },
            },
            "handlers": {
                "rich": {
                    "class": "rich.logging.RichHandler",
                    "markup": True,
                    "rich_tracebacks": True,
                    "formatter": "rich",
                },
            },
            "root": {
                "handlers": ["rich"],
                "level": "INFO",
            },
        },
    )
