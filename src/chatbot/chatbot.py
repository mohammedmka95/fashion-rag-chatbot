"""
chatbot.py
----------
Core chatbot logic for the "Fashion Forward Hub" store assistant.

The chatbot can answer two kinds of questions:
  1. FAQ questions (return policy, working hours, etc.)
  2. Product questions (find/recommend clothing items from the catalogue)

It uses:
  - Groq's LLM API (via utils.py) to classify queries and generate answers.
  - A Weaviate instance that already holds the data in two collections:
      * "products" - the clothing catalogue, used for vector search / filtering
      * "faq"      - the FAQ entries, read in full to build the FAQ context
    Weaviate is required (both FAQ and product answers depend on it).

This module contains no notebook-specific code (no display(), no widgets).
"""

from weaviate.classes.query import Filter
from weaviate.classes.aggregate import GroupByAggregate

from utils.utils import (
    generate_with_single_input,
    generate_params_dict,
    parse_json_output,
    generate_faq_layout,
    generate_items_context,
    call_llm_with_context,
)


# Metadata keys used to filter the product catalogue.
FILTERABLE_KEYS = (
    "gender",
    "masterCategory",
    "articleType",
    "baseColour",
    "price",
    "usage",
    "season",
)

# Product properties (excluding 'price') whose distinct values are fetched
# from Weaviate to constrain the LLM when building metadata filters.
METADATA_PROPERTIES = ("gender", "masterCategory", "articleType", "baseColour", "usage", "season")

# Order in which filters are dropped (least -> most important) when a query
# returns too few results and needs to be broadened.
FILTER_IMPORTANCE_ORDER = ["baseColour", "masterCategory", "usage", "masterCategory", "season", "gender"]


class FashionChatBot:
    """
    A terminal chatbot for a fictional clothing store, "Fashion Forward Hub".

    Responsibilities:
      - Read the FAQ entries and product metadata from Weaviate.
      - Route each user query to the FAQ or Product workflow.
      - Retrieve relevant products from Weaviate via vector search + filters.
      - Keep track of conversation history for context-aware replies.
    """

    def __init__(
        self,
        weaviate_client,
        model: str = "llama-3.3-70b-versatile",
        context_window: int = 20,
        products_collection_name: str = "products",
        faq_collection_name: str = "faq",
    ):
        if weaviate_client is None:
            raise ValueError(
                "A Weaviate client is required — both the FAQ and product "
                "workflows read their data from Weaviate."
            )

        self.model = model
        self.context_window = context_window

        # --- Weaviate collections (data already loaded into Weaviate) --------------
        self.client = weaviate_client
        self.products_collection = self.client.collections.get(products_collection_name)
        self.faq_collection = self.client.collections.get(faq_collection_name)

        # --- Load FAQ entries and build the FAQ prompt layout -----------------------
        self.faq_data = self._load_faq_from_weaviate()
        self.faq_layout = generate_faq_layout(self.faq_data)

        # --- Discover possible product metadata values (for filter generation) -----
        self.metadata_values = self._extract_possible_metadata_values()

        # --- Conversation state ------------------------------------------------------
        self.system_prompt = {
            "role": "system",
            "content": (
                "You are a friendly assistant from Fashion Forward Hub. "
                "It is a cloth store selling a variety of items. "
                "Your job is to answer questions related to FAQ or Products."
            ),
        }
        self.initial_message = {
            "role": "assistant",
            "content": "Hi! How can I help you?",
        }
        self.conversation = [self.system_prompt, self.initial_message]

    # ------------------------------------------------------------------------- #
    # Setup helpers
    # ------------------------------------------------------------------------- #
    def _load_faq_from_weaviate(self) -> list:
        """
        Read every object out of the "faq" collection. Each object is
        expected to have 'question', 'answer', and 'type' properties.
        """
        return [obj.properties for obj in self.faq_collection.iterator()]

    def _extract_possible_metadata_values(self) -> dict:
        """
        Build a dict mapping each relevant product attribute to the set of
        possible values found in the catalogue, using Weaviate's aggregate
        group-by so the full product list never has to be pulled locally.
        Used to constrain the LLM when it generates metadata filters from a
        natural-language query.
        """
        values = {}
        for prop in METADATA_PROPERTIES:
            try:
                response = self.products_collection.aggregate.over_all(
                    group_by=GroupByAggregate(prop=prop)
                )
                values[prop] = {group.grouped_by.value for group in response.groups}
            except Exception as e:
                print(f"[warning] Could not fetch distinct values for '{prop}': {e}")
                values[prop] = set()
        return values

    # ------------------------------------------------------------------------- #
    # Step 0: Fold prior conversation context into a self-contained query
    # ------------------------------------------------------------------------- #
    def _condense_query(self, user_input: str) -> str:
        """
        Rewrite the user's latest message into a single, self-contained query
        by folding in relevant details mentioned earlier in the conversation
        (gender, color, category, price, occasion, etc.).

        This matters for short follow-up replies like "for men" or "yes"
        that only make sense in light of the previous turn(s) — without this
        step, downstream classification/filtering sees just "yes" and has
        nothing to build filters from, so it silently falls back to a
        generic, non-product-grounded answer instead of real retrieval.
        """
        # Everything except the system prompt and the initial greeting.
        history_turns = [
            m for m in self.conversation[-self.context_window:]
            if m is not self.system_prompt and m is not self.initial_message
        ]

        # Nothing to fold in yet — the message already stands on its own.
        if not history_turns:
            return user_input

        history_text = "\n".join(f'{m["role"]}: {m["content"]}' for m in history_turns)

        prompt = f"""
        You are given a running conversation between a user and a clothing store assistant, followed by the user's latest message.
        Rewrite the latest message into a single, fully self-contained question that folds in any relevant details mentioned earlier in the conversation (e.g. gender, color, category, price range, occasion).
        Do not answer the question — only rewrite it as a question or request.
        If the latest message is already self-contained and needs no extra context, return it unchanged.
        Return only the rewritten message, nothing else — no labels, no explanations.

        Conversation so far:
        {history_text}

        Latest message: {user_input}
        """
        kwargs = generate_params_dict(prompt, temperature=0)
        response = generate_with_single_input(**kwargs)
        condensed = response["content"].strip()
        return condensed or user_input

    # ------------------------------------------------------------------------- #
    # Step 1: Route the query to FAQ or Product
    # ------------------------------------------------------------------------- #
    def check_if_faq_or_product(self, query: str) -> str:
        """
        Classify a query as 'FAQ' or 'Product' related using the LLM.
        Returns None if the label is inconclusive.
        """
        prompt = f"""
        Label the following instruction as an FAQ-related query or a product-related query.
        Product-related answers are specific to product information or require using product details to answer. Products are clothes from a store.
        An FAQ question addresses common inquiries and provides answers to help users find the information they need.
        Examples:
                Is there a refund for incorrectly bought clothes? Label: FAQ
                Tell me about the cheapest T-shirts that you have. Label: Product
                Do you have blue T-shirts under 100 dollars? Label: Product
                I bought a T-shirt and I didn't like it. How can I get a refund? Label: FAQ
                What is your return policy? Label: FAQ
                Give me three examples of blue T-shirts you have available. Label: Product
                How can I contact the user support? Label: FAQ
                Do you have blue Dresses? Label: Product
                Create a look suitable for a wedding party happening during dawn. Label: Product

        Return only one of the two labels: FAQ or Product.
        Instruction: {query}
        """
        kwargs = generate_params_dict(prompt, temperature=0.3)
        response = generate_with_single_input(**kwargs)
        label = response["content"].strip()

        if label not in ["FAQ", "Product"]:
            return None
        return label

    # ------------------------------------------------------------------------- #
    # Step 2a: FAQ workflow
    # ------------------------------------------------------------------------- #
    def query_on_faq(self, query: str, **kwargs) -> dict:
        """
        Build the LLM call parameters needed to answer a query using the FAQ.
        """
        prompt = f"""
        You will be provided with an FAQ for a cloth store.
        Answer the instruction based on it. You might use more than one question and answer to make your answer.
        Only answer the question and do not mention that you have access to a FAQ.
        <FAQ>
        PROVIDED FAQ: {self.faq_layout}
        </FAQ>
        Question: {query}
        """
        return generate_params_dict(prompt, **kwargs)

    # ------------------------------------------------------------------------- #
    # Step 2b: Product workflow
    # ------------------------------------------------------------------------- #
    def decide_task_nature(self, query: str) -> str:
        """
        Classify a product query as 'creative' (e.g. outfit suggestions) or
        'technical' (e.g. specific product lookups).
        """
        prompt = f"""
        Decide if the following query is a query that requires creativity (creating, composing, making new things) or technical (information about products, prices, etc.). Label it as creative or technical.
        Examples:
        Give me suggestions on a nice look for a nightclub. Label: creative
        What are the blue dresses you have available? Label: technical
        Give me three T-shirts for summer. Label: technical
        Give me a look for attending a wedding party. Label: creative
        Give me two sneakers with vibrant colors. Label: technical
        What are the most expensive clothes you have in your catalogue? Label: technical
        I have a green dress and I like a suggestion on an accessory to match with it. Label: creative
        Give me three trousers with vibrant colors you have in your catalogue. Label: technical
        Create a look for a woman walking in a park on a sunny day. It must be fresh due to hot weather. Label: creative

        Query to be analyzed: {query}. Only output one token: the label.
        """
        kwargs = generate_params_dict(prompt, temperature=0, max_tokens=1)
        response = generate_with_single_input(**kwargs)
        return response["content"].strip().lower()

    @staticmethod
    def get_params_for_task(task: str) -> dict:
        """
        Return sampling parameters (top_p / temperature) tuned for a
        creative or technical task. Falls back to a middle-ground default
        for unrecognized task labels.
        """
        parameters_dict = {
            "creative": {"top_p": 0.9, "temperature": 1.0},
            "technical": {"top_p": 0.5, "temperature": 0.3},
        }
        return parameters_dict.get(task, {"top_p": 0.7, "temperature": 0.5})

    def generate_metadata_from_query(self, query: str) -> str:
        """
        Ask the LLM to produce a JSON object of product metadata filters
        (gender, category, color, price range, etc.) inferred from the query.
        """
        prompt = f"""
        A query will be provided. Based on this query, a vector database will be searched to find relevant clothing items.
        Generate a JSON object containing useful metadata to filter products for this query.
        The possible values for each feature are given in the following JSON: {self.metadata_values}

        Provide a JSON containing the features that best match the query (values should be in lists, multiple values possible).
        If a price range is mentioned, include a price key specifying the range (between values, greater than, or less than).
        Return only the JSON, nothing else. The price key must be a JSON object with "min" and "max" values (use 0 if no lower bound, and "inf" if no upper bound).
        Always include the following keys: gender, masterCategory, articleType, baseColour, price, usage, and season.
        If no price is specified, set min = 0 and max = inf.
        Include only values present in the JSON above.

        Example of expected JSON:

        {{
          "gender": ["Women"],
          "masterCategory": ["Apparel"],
          "articleType": ["Dresses"],
          "baseColour": ["Blue"],
          "price": {{"min": 0, "max": "inf"}},
          "usage": ["Formal"],
          "season": ["All seasons"]
        }}

        Query: {query}
        """
        kwargs = generate_params_dict(prompt, temperature=0, max_tokens=1500)
        response = generate_with_single_input(**kwargs)
        return response["content"]

    @staticmethod
    def get_filter_by_metadata(json_output: dict = None):
        """
        Convert a metadata dict (produced by generate_metadata_from_query +
        parse_json_output) into a list of Weaviate Filter objects.
        """
        if json_output is None:
            return None

        filters = []
        for key, value in json_output.items():
            if key not in FILTERABLE_KEYS:
                continue

            if key == "price":
                if not isinstance(value, dict):
                    continue
                min_price = value.get("min")
                max_price = value.get("max")
                if min_price is None or max_price is None:
                    continue
                if min_price <= 0 or max_price == "inf":
                    continue
                filters.append(Filter.by_property(key).greater_than(min_price))
                filters.append(Filter.by_property(key).less_than(max_price))
            else:
                filters.append(Filter.by_property(key).contains_any(value))

        return filters

    def generate_filters_from_query(self, query: str) -> list:
        """
        Full pipeline: query -> metadata JSON -> parsed dict -> Weaviate filters.
        """
        json_string = self.generate_metadata_from_query(query)
        json_output = parse_json_output(json_string)
        return self.get_filter_by_metadata(json_output)

    def get_relevant_products_from_query(self, query: str):
        """
        Retrieve relevant products for a query, broadening the search
        (dropping filters) if too few results are found.
        """
        filters = self.generate_filters_from_query(query)

        if not filters:
            return self.products_collection.query.near_text(query, limit=20).objects

        res = self.products_collection.query.near_text(
            query, filters=Filter.all_of(filters), limit=20
        ).objects

        if len(res) < 10:
            for i in range(len(FILTER_IMPORTANCE_ORDER)):
                remaining_filters = [
                    f for f in filters if f.target not in FILTER_IMPORTANCE_ORDER[i + 1:]
                ]
                res = self.products_collection.query.near_text(
                    query, filters=Filter.all_of(remaining_filters), limit=20
                ).objects
                if len(res) >= 5:
                    return res
            if len(res) < 5:
                res = self.products_collection.query.near_text(query, limit=20).objects

        return res

    def query_on_products(self, query: str) -> dict:
        """
        Full product-answering pipeline: decide the query's nature, fetch
        relevant products, and build the LLM call parameters for the answer.
        """
        query_label = self.decide_task_nature(query)
        parameters_dict = self.get_params_for_task(query_label)

        relevant_products = self.get_relevant_products_from_query(query)
        context = generate_items_context(relevant_products)

        prompt = (
            f"Given the available set of cloth products, answer the question that follows, providing the item ID in your answers. "
            f"Other information might be provided but not necessarily all of them; pick only the relevant ones for the given query and avoid being too long when describing the items' features. "
            f"If no number of products is mentioned in the query, select at most five to show. "
            f"You must recommend only items from the CLOTH PRODUCTS AVAILABLE list below, each with its real Product ID. "
            f"Do not give generic store advice or suggest browsing a section instead of listing items — always list specific products. "
            f"If the list below is empty, say so plainly instead of inventing products. "
            f"CLOTH PRODUCTS AVAILABLE: {context} "
            f"QUERY: {query}"
        )
        return generate_params_dict(prompt, role="user", **parameters_dict)

    # ------------------------------------------------------------------------- #
    # Top-level router: "the function to rule them all"
    # ------------------------------------------------------------------------- #
    def answer_query(self, query: str) -> dict:
        """
        Determine whether a query is FAQ or Product related and build the
        appropriate LLM call parameters. Falls back to a generic response
        if classification is inconclusive or product search fails.
        """
        label = self.check_if_faq_or_product(query)

        if label not in ["FAQ", "Product"]:
            return {
                "role": "user",
                "prompt": (
                    "User provided a question that does not fit FAQ or Product related questions. "
                    f"Answer it based on the context you already have so far. Query provided by the user: {query}"
                ),
            }

        if label == "FAQ":
            return self.query_on_faq(query)

        # label == "Product"
        try:
            return self.query_on_products(query)
        except Exception:
            return {
                "role": "user",
                "prompt": (
                    "User provided a question that broke the querying system. Instruct them to rephrase it. "
                    f"Answer it based on the context you already have so far. Query provided by the user: {query}"
                ),
            }

    # ------------------------------------------------------------------------- #
    # Conversation handling
    # ------------------------------------------------------------------------- #
    def chat(self, prompt: str) -> str:
        """
        Handle a single round of user interaction: fold in prior context so
        short follow-ups are self-contained, route the resulting query, call
        the LLM with full conversation context, store the exchange in the
        conversation history, and return the assistant's reply text.
        """
        recent_context = self.conversation[-self.context_window:]

        # Resolve short/context-dependent follow-ups (e.g. "for men", "yes")
        # into a standalone query before classification, filtering, and
        # retrieval — but keep the user's original wording in history below.
        resolved_prompt = self._condense_query(prompt)

        params_dict = self.answer_query(resolved_prompt)
        params_dict["model"] = self.model

        response = call_llm_with_context(context=recent_context, **params_dict)

        self.conversation.append({"role": "user", "content": prompt})
        self.conversation.append(recent_context[-1])

        return response["content"]

    def clear_conversation(self) -> None:
        """Reset the conversation history back to its initial state."""
        self.conversation = [self.system_prompt, self.initial_message]
