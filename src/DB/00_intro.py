import weaviate
import json
print(f"Your Weaviate client library version is: {weaviate.__version__}.")

client = weaviate.connect_to_local()



try:
    # Work with the client here - e.g.:
    assert client.is_ready()
    print(client.is_ready())

    #------------------------


    # metainfo = client.get_meta()
    # print(json.dumps(metainfo, indent=2))  # Print the meta information in a readable format

    #------------------------

finally:  # This will always be executed, even if an exception is raised
    client.close()