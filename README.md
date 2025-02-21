# How to use:
```shell
pip install ariadne-auth
```

### Set your Authorization Extension with global permissions

```python
from graphql import GraphQLResolveInfo
from ariadne_auth.authz import AuthorizationExtension
from ariadne_auth.types import HasPermissions


# Define a function that returns the permission object
def get_permission_obj(info: GraphQLResolveInfo) -> HasPermissions:
    return info.context["my_permission_obj"]

# it can be also an async function
async def get_permission_obj_async(info: GraphQLResolveInfo) -> HasPermissions:
    return info.context["my_permission_obj"]


# Instantiate the AuthorizationExtension
authz = AuthorizationExtension(permissions_object_provider_fn=get_permission_obj)

# Set list of permissions required for all resolvers 
authz.set_required_global_permissions(["user:logged_in"])
```


### Configure resolvers
```python
query = QueryType()
ship = ObjectType("Ship")
faction = ObjectType("Faction")

# Set additional required permissions for specific resolvers
@query.field("rebels")
@authz.require_permissions(permissions=["read:rebels"])
async def resolve_rebels(*_):
    return FACTIONS[0]


@query.field("empire")
@authz.require_permissions(permissions=["read:empire"], ignore_global_permissions=False)
async def resolve_empire(*_):
    return FACTIONS[1]



# Disable global permissions for specific resolver
@query.field("ships")
@authz.require_permissions(permissions=[], ignore_global_permissions=True)
async def resolve_ships(obj, *_):
    return SHIPS

# Note the global permission is set on default_field_resolver it requires to disable permissions explicity
@ship.field("name")
@authz.require_permissions(permissions=[], ignore_global_permissions=True)
async def resolve_ship_name(obj, *_):
    return obj["name"]
```

If needed you may also overwrite the function to get the permission object
```python
def get_ship_permissions(info: GraphQLResolveInfo) -> HasPermissions:
    return info.context["my_ship_permission_obj"]

@ship.field("name")
@authz.require_permissions(
    permissions=[],
    ignore_global_permissions=True,
    permissions_object_provider_fn=get_ship_permissions
)
async def resolve_ship_name(obj, *_):
    return obj["name"]

```


### Add your extension to Ariadne GraphQL instance
```python
app = GraphQL(
    schema,
    http_handler=GraphQLHTTPHandler(extensions=[authz]),  # add the authz extension
)
```
 
You may also pass `authz` instance into info.context to use it directly 

use `_auth.assert_permissions` or `await _auth.assert_permissions_async` to check permissions in your resovlers
```python
# Depends on the faction, additional permissions are required
@faction.field("ships")
async def resolve_faction_ships(faction_obj, info: GraphQLResolveInfo, *_):
    _auth = info.context["auth"]
    if (
        faction_obj["name"] == "Alliance to Restore the Republic"
    ):  # Rebels faction requires additional perm to read ships
        _auth.assert_permissions(_auth.permissions_object_provider_fn(info), ["read:ships"])

    return [_ship for _ship in SHIPS if _ship["factionId"] == faction_obj["id"]]

def get_context_value(request, data):
    return {
        **authz.generate_authz_context(request),
    }


app = GraphQL(
    schema,
    context_value=get_context_value,
    http_handler=GraphQLHTTPHandler(extensions=[authz])
)
```


## Run test app 
The repository contains a test application that demonstrates how to use the library

#### To run test application use: `hatch run ariadne_auth`
Note that `user_id` is hardcoded in `app.py:104`


### Example request
for user with permissions
```
    permissions=[
        "user:logged_in",
        "read:empire",
        "read:rebels",
    ],  # can't read rebels ships
```
```graphql
query {
  empire{
    id
    name
    ships {
      id
      name
    }
  }
  rebels{
    id
    name
    ships {
      name
    }
  }
  ships {
    name
  }
}
```



**Crafted with ❤️ by [Mirumee Software](https://mirumee.com)**
hello@mirumee.com