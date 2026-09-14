import weaviate
from weaviate.classes.config import Configure, Property, DataType

client = weaviate.connect_to_local()

# 1. Create Products Collection
client.collections.create(
    name="products",
    properties=[
        Property(name="gender", data_type=DataType.TEXT),
        Property(name="masterCategory", data_type=DataType.TEXT),
        Property(name="subCategory", data_type=DataType.TEXT),
        Property(name="articleType", data_type=DataType.TEXT),
        Property(name="baseColour", data_type=DataType.TEXT),
        Property(name="season", data_type=DataType.TEXT),
        Property(name="year", data_type=DataType.NUMBER),
        Property(name="usage", data_type=DataType.TEXT),
        Property(name="productDisplayName", data_type=DataType.TEXT),
        Property(name="price", data_type=DataType.NUMBER),
        Property(name="product_id", data_type=DataType.INT),
    ],
    vector_config=Configure.Vectors.text2vec_transformers()
)

# 2. Create FAQ Collection
client.collections.create(
    name="faq",
    properties=[
        Property(name="question", data_type=DataType.TEXT),
        Property(name="answer", data_type=DataType.TEXT),
        Property(name="type", data_type=DataType.TEXT),
    ],
    vector_config=Configure.Vectors.text2vec_transformers()
)

client.close()