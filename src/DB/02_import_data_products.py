import weaviate
import joblib
from tqdm import tqdm
from weaviate.util import generate_uuid5

client = weaviate.connect_to_local()

try:
    # Load products from joblib
    products_data = joblib.load("dataset/clothes_json.joblib")

    products = client.collections.use("products")

    with products.batch.fixed_size(batch_size=200) as batch:

        for row in tqdm(products_data, total=len(products_data)):

            product_obj = {
                "gender": str(row.get("gender", "")),
                "masterCategory": str(row.get("masterCategory", "")),
                "subCategory": str(row.get("subCategory", "")),
                "articleType": str(row.get("articleType", "")),
                "baseColour": str(row.get("baseColour", "")),
                "season": str(row.get("season", "")),
                "year": (
                    float(row["year"])
                    if row.get("year") is not None
                    else None
                ),
                "usage": str(row.get("usage", "")),
                "productDisplayName": str(
                    row.get("productDisplayName", "")
                ),
                "price": float(row.get("price", 0.0)),
                "product_id": int(row["product_id"])
            }

            batch.add_object(
                properties=product_obj,
                uuid=generate_uuid5(
                    str(row["product_id"])
                )
            )

    if products.batch.failed_objects:
        print(
            f"Failed objects: "
            f"{len(products.batch.failed_objects)}"
        )

finally:
    client.close()