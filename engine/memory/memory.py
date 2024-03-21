import logging
import time
import uuid
from enum import Enum
from typing import List

from pydantic.v1 import BaseModel, Field
from pymilvus import connections, Collection, FieldSchema, DataType, CollectionSchema
from pymilvus.orm import utility
from sentence_transformers import SentenceTransformer

from engine.models import Task
from engine.util import slugify

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Establish connection to Milvus
connections.connect("default", host="localhost", port="19530")


def get_collection(collection_name):
    collection_name = collection_name.replace("-", "_")
    fields = [
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=384),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=1024),
        FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=20),
        FieldSchema(name="task_id", dtype=DataType.VARCHAR, max_length=128),
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    ]
    schema = CollectionSchema(fields, description="LLM Memory Storage")
    if not utility.has_collection(collection_name):
        collection = Collection(name=collection_name, schema=schema)
        index_params = {
            "metric_type": "IP",  # or "IP" for inner product (cosine similarity)
            "index_type": "IVF_FLAT",  # You can choose other index types like HNSW, ANNOY, etc.
            "params": {"nlist": 1024}  # Number of clusters to partition the vectors, adjust based on your dataset
        }

        # Create an index on the vector field
        collection.create_index(field_name="vector", index_params=index_params)
        logger.info(f"Collection '{collection_name}' created.")
    else:
        collection = Collection(name=collection_name)
        logger.info(f"Collection '{collection_name}' already exists.")
    collection.load()
    utility.wait_for_loading_complete(collection_name)
    return collection


# Initialize SentenceTransformer model
model = SentenceTransformer('all-MiniLM-L6-v2')


class MemoryCategory(Enum):
    """Categories of memories"""
    USER_PREFERENCE = "user_preference"
    LIBRARY = "library"
    FRAMEWORK = "framework"
    CLASS = "class"


class Memory(BaseModel):
    """A memory"""
    category: MemoryCategory = Field(description="Category of the memory")
    text: str = Field(description="Text of the memory")


class MemorySearchResult(BaseModel):
    """A result from searching the vector store"""
    score: float = Field(description="Similarity score")
    memory: Memory = Field(description="Memory")


def insert_memory(text, category, task: Task):
    logger.info(f"Inserting memory: {text}")
    # Vectorize text
    vector = model.encode([text])  # Ensure text is passed as a list

    # Prepare data for Milvus (fix structure to match expected format)
    entities = [
        vector.tolist(),  # Convert numpy array to list
        [text],
        [category],
        [str(task.id)],
    ]

    # Insert data into the collection
    collection = get_collection(slugify(task.github_project))
    mr = collection.insert(entities)
    logger.info(f"Inserted ID: {mr.primary_keys}")
    return mr.primary_keys  # Returns the ID(s) of the inserted record(s)

def search_memories(text, task: Task, top_k=3) -> List[MemorySearchResult]:
    logger.info(f"Searching memory for: {text}")
    # Vectorize query text
    query_vector = model.encode([text])  # Ensure text is passed as a list

    # Perform the search
    search_params = {
        "metric_type": "IP",
        "params": {"nprobe": 10},
    }
    collection = get_collection(slugify(task.github_project))
    results = collection.search(
        data=query_vector.tolist(),
        anns_field="vector",
        param=search_params,
        limit=top_k,
        expr=None,
        output_fields=["category", "text"]
    )

    # Process and log results
    search_results = []
    for hits in results:
        for hit in hits:
            memory = Memory(category=MemoryCategory(hit.entity.get("category")), text=hit.entity.get("text"))
            search_results.append(MemorySearchResult(score=hit.score, memory=memory))
            logger.info(f"ID: {hit.id}, Score: {hit.score}, Metadata: {hit.entity}")
    return search_results

if __name__ == '__main__':
    text = "I need to install a Python package."
    category = "installation"
    task_id = 123  # Ensure this is unique for each insert
    memories = [
        ["Uses `Django` as webframework", "framework", str(uuid.uuid4())],
        ["Uses `langchain` for LLM interactions", "library", str(uuid.uuid4())],
        ["Uses `pymilvus` for vector storage", "library", str(uuid.uuid4())],
        ["Uses pytest for testing", "tools", str(uuid.uuid4())],

    ]
    try:
        for memory in memories:
            insert_memory(*memory)
        # time.sleep(2)  # Ensure the insert is complete before searching
        time.sleep(5)
        search_memories('How do I interact with LLMs')
    finally:
        collection.drop()
        pass
