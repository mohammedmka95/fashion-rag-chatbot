import weaviate
import json
print(f"Your Weaviate client library version is: {weaviate.__version__}.")

client = weaviate.connect_to_local()

try:
    # Work with the client here - e.g.:
    assert client.is_ready()
    print(client.is_ready())

    #------------------------
    # Get the FAQ collection and perform a semantic search
    faq_collection = client.collections.get('faq')
    results = faq_collection.query.near_text(query="How do I return an item?", limit=3)
    
    # Print the FAQ results
    print("\nFAQ Search Results:")
    for i, result in enumerate(results.objects, 1):
        print(f"\nResult {i}:")
        print(f"  Question: {result.properties['question']}")
        print(f"  Answer: {result.properties['answer']}")
        print(f"  Type: {result.properties['type']}")

        
    #------------------------
    
    # Get the Products collection and perform a semantic search
    products_collection = client.collections.get('products')
    products_results = products_collection.query.near_text(query="blue t-shirt for summer", limit=3)
    
    # Print the Products results
    print("\nProducts Search Results:")
    for i, result in enumerate(products_results.objects, 1):
        print(f"\nResult {i}:")
        print(f"  Product ID: {result.properties['product_id']}")
        print(f"  Product Name: {result.properties['productDisplayName']}")
        print(f"  Gender: {result.properties['gender']}")
        print(f"  Category: {result.properties['masterCategory']}")
        print(f"  Sub Category: {result.properties['subCategory']}")
        print(f"  Article Type: {result.properties['articleType']}")
        print(f"  Color: {result.properties['baseColour']}")
        print(f"  Season: {result.properties['season']}")
        print(f"  Usage: {result.properties['usage']}")
        print(f"  Price: ${result.properties['price']}")

    #------------------------

finally:  # This will always be executed, even if an exception is raised
    client.close()