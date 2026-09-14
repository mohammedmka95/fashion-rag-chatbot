import weaviate
from weaviate.classes.query import MetadataQuery

client = weaviate.connect_to_local()

products = client.collections.use("products")

response = products.query.bm25(
    query="black running shoes",
    limit=5,
    return_metadata=MetadataQuery(score=True)
)

for product in response.objects:
    print(f"Name      : {product.properties['productDisplayName']}")
    print(f"Gender    : {product.properties['gender']}")
    print(f"Category  : {product.properties['masterCategory']}")
    print(f"Type      : {product.properties['articleType']}")
    print(f"Color     : {product.properties['baseColour']}")
    print(f"Price     : ${product.properties['price']:.2f}")
    print(f"BM25 Score: {product.metadata.score:.3f}")
    print("-" * 50)

client.close()