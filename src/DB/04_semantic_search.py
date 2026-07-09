import weaviate
from weaviate.classes.query import MetadataQuery

client = weaviate.connect_to_local()

products = client.collections.use("products")

response = products.query.near_text(
    query="red summer running shoes for men",
    limit=5,
    return_metadata=MetadataQuery(distance=True)
)

for obj in response.objects:
    print(f"Name      : {obj.properties['productDisplayName']}")
    print(f"Gender    : {obj.properties['gender']}")
    print(f"Category  : {obj.properties['masterCategory']}")
    print(f"SubCat    : {obj.properties['subCategory']}")
    print(f"Type      : {obj.properties['articleType']}")
    print(f"Color     : {obj.properties['baseColour']}")
    print(f"Season    : {obj.properties['season']}")
    print(f"Usage     : {obj.properties['usage']}")
    print(f"Price     : ${obj.properties['price']}")
    print(f"Distance  : {obj.metadata.distance:.3f}")
    print("-" * 50)

client.close()