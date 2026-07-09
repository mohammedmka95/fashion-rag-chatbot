from datetime import datetime, timezone
import weaviate
from weaviate.classes.query import Filter, MetadataQuery

client = weaviate.connect_to_local()

try:
    products = client.collections.use("products")

    response = products.query.near_text(
        query="black running shoes for men",
        limit=5,
        return_metadata=MetadataQuery(distance=True),
        filters=Filter.by_property("gender").equal("Men")  
    )

    for product in response.objects:
        print(f"Name      : {product.properties['productDisplayName']}")
        print(f"Gender    : {product.properties['gender']}")
        print(f"Category  : {product.properties['masterCategory']}")
        print(f"Type      : {product.properties['articleType']}")
        print(f"Color     : {product.properties['baseColour']}")
        print(f"Price     : ${product.properties['price']:.2f}")
        print(f"Distance  : {product.metadata.distance:.3f}\n")  # Fixed: changed 'o' to 'product'
        print()

finally:
    client.close()