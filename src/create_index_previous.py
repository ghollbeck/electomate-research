from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.core.node_parser import SimpleNodeParser
from tqdm import tqdm
from config import api_key, chunk_size, chunk_overlap  # Import the API key and chunk settings from config
import os

# Set the API key from config
os.environ["OPENAI_API_KEY"] = api_key

print("Loading documents...")
documents = SimpleDirectoryReader("downloaded_pdfs").load_data()

# Create a node parser with custom chunk size
node_parser = SimpleNodeParser.from_defaults(
    chunk_size=chunk_size,
    chunk_overlap=chunk_overlap
)

# Parse documents into nodes (chunks) with progress bar
print("Generating chunks...")
nodes = []
for doc in tqdm(documents, desc="Processing documents", unit="doc"):
    doc_nodes = node_parser.get_nodes_from_documents([doc])
    nodes.extend(doc_nodes)

print(f"Generated {len(nodes)} chunks in total")

print("Creating index...")
with tqdm(total=len(nodes), desc="Indexing chunks", unit="chunk") as pbar:
    index = VectorStoreIndex(nodes=nodes)
    pbar.update(len(nodes))

print("Persisting index to disk...")
index.storage_context.persist(persist_dir="index_store2")
print("Done!")