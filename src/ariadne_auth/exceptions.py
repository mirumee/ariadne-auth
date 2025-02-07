from graphql import GraphQLError


class GraphQLErrorAuthorizationError(GraphQLError):
    def __init__(self, message: str = "Permission denied") -> None:
        super().__init__(
            message, extensions={"Authorization": {"errorType": "UNAUTHORIZED"}}
        )
