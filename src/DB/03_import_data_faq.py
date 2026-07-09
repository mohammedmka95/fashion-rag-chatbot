import weaviate
import joblib
from tqdm import tqdm
from weaviate.util import generate_uuid5

client = weaviate.connect_to_local()

try:
    # Load FAQs from joblib
    faq_data = joblib.load("dataset/faq.joblib")

    faq = client.collections.use("faq")

    with faq.batch.fixed_size(batch_size=200) as batch:

        for row in tqdm(faq_data, total=len(faq_data)):

            faq_obj = {
                "question": str(row["question"]),
                "answer": str(row["answer"]),
                "type": str(row["type"]),
            }

            batch.add_object(
                properties=faq_obj,
                uuid=generate_uuid5(row["question"])
            )

    if faq.batch.failed_objects:
        print(
            f"Failed objects: "
            f"{len(faq.batch.failed_objects)}"
        )

finally:
    client.close()