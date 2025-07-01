import os
from dotenv import load_dotenv
import chromadb
from chromadb.utils import embedding_functions
from config import SCHEMA_TABLES, RELATIONSHIPS  # Import your schema definitions
from datetime import datetime  # ✅ Fix: Add this to define current_year

# Load environment variables
load_dotenv()
openai_key = os.getenv("OPENAI_API_KEY")
if not openai_key:
    raise ValueError("OPENAI_API_KEY not found in .env file")

# ✅ Initialize ChromaDB client and embedding function
chroma_client = chromadb.PersistentClient(path="./chroma_db")
embedding_fn = embedding_functions.OpenAIEmbeddingFunction(
    api_key=openai_key,
    model_name="text-embedding-3-small"
)

# ✅ Create or get collection
collection = chroma_client.get_or_create_collection(
    name="sql_schema_chunks",
    embedding_function=embedding_fn  # type: ignore
)

# ✅ Optional: Clear existing data
existing_ids = collection.get().get("ids", [])
if existing_ids:
    collection.delete(ids=existing_ids)
    print(f"🗑 Cleared {len(existing_ids)} existing chunks from collection.")

# ✅ Add schema tables as chunks
for i, table_schema in enumerate(SCHEMA_TABLES):
    cleaned_schema = table_schema.strip()
    collection.add(
        documents=[cleaned_schema],
        ids=[f"table_chunk_{i+1}"],
        metadatas=[{"type": "schema_table"}]
    )
    print(f"✅ Stored table chunk {i+1}:\n{cleaned_schema}\n{'-'*60}")

# ✅ Add relationships
if RELATIONSHIPS.strip():
    collection.add(
        documents=[RELATIONSHIPS.strip()],
        ids=["relationships_chunk"],
        metadatas=[{"type": "schema_relationships"}]
    )
    print(f"🔗 Stored relationships chunk:\n{RELATIONSHIPS.strip()}\n{'='*60}")

# ✅ Define current year
current_year = datetime.now().year

# ✅ Define and add SQL generation rule chunks
from datetime import datetime

current_year = datetime.now().year

RULES_CHUNKS = [
    f"""
📌 Core JOIN Rule:
- Always JOIN listings when selecting or filtering by l.price_night or price-related info:
  → JOIN listings l ON r.id = l.resort_id
- This JOIN must come *before* the WHERE clause, grouped with other JOINs.
- Always include listings join if using l.price_night in SELECT or WHERE.
- Use LEFT JOIN only if resorts without listings should still appear.

🌍 Location Matching Rules:
- If the user mentions a U.S. state or country (e.g., "California", "Florida", "India"):
  → Treat them as part of r.address using:
    LOWER(r.address) LIKE '%<location>%'
  → Do NOT use location_types or r.city in this case.
- Use only one location field in SELECT:
  → Prefer r.city for city-level queries.
  → Use r.address only when states or countries are mentioned.
  → *Do NOT include both r.city and r.address in SELECT.*

✅ Resort Info Requirements:
- Use only these fields: r.name, (r.city or r.address), r.highlight_quote, l.price_night, r.slug.
- Always use this for price:
  CAST(NULLIF(l.price_night, '') AS DECIMAL(10,2)) AS price
- Results must be descriptive and useful to users.
- SQL must return readable resort summaries.

🔒 General SQL Rules:
- Assume current year: "{current_year}" unless user specifies another.
- Use only l.price_night for price — ignore any others.
- SQL only — no markdown, explanation, formatting, or extra comments.

📆 Availability Rules:
- Use check-in/check-out only when the user explicitly mentions date filters:
  → l.check_in <= 'YYYY-MM-DD 00:00:00' AND l.check_out >= 'YYYY-MM-DD 00:00:00'

🏷 Amenity Rules:
- Join amenities only when the query involves specific amenities.
  → Use:
    JOIN resort_amenities ra ON r.id = ra.resort_id
    JOIN amenities a ON ra.amenity_id = a.id
    REPLACE(LOWER(a.name), ' ', '') LIKE '%<normalized_amenity>%'
- If user says “important” or “key amenities”, add:
  a.is_key_amenity = 1

🌄 Location Type Rules:
- Join location_types only if the user asks for types like "Beach", "Mountain", "Lake", etc.
  → Use:
    JOIN location_types lt ON r.id = lt.resort_id AND lt.types = '<type>'
  → Never use lt.city or lt.state.
  → Do NOT confuse place names with types.

🎯 WHERE Clause Rules:
- Always include these base conditions:
  r.status = 'active' AND r.has_deleted = 0
- Add additional WHERE filters only if required by the query intent.

🛠 Join Only If Needed:
- Only include JOINs for tables whose fields are used in SELECT or WHERE.
- Do not add unnecessary joins.
- Always use correct aliases (r, l, a, ra, lt) and valid column names.

📐 SQL Formatting Rules:
- Use GROUP BY or aggregates (COUNT, AVG, etc.) only when needed.
- Fields in ORDER BY must also appear in SELECT.
- Use DISTINCT or GROUP BY to eliminate duplicates when listing resorts.
- Always end SQL with a semicolon (;).

🛡 Validation Safeguards:
- JOINs must come between FROM and WHERE — never after WHERE.
- If l.price_night is used, listings JOIN must be present.
- SELECT must only include valid fields from the joined tables.
"""
]


# ✅ Store rules into vector DB
for i, rule_text in enumerate(RULES_CHUNKS):
    cleaned_rule = rule_text.strip()
    collection.add(
        documents=[cleaned_rule],
        ids=[f"rule_chunk_{i+1}"],
        metadatas=[{"type": "rule"}]
    )
    print(f"📜 Stored rule chunk {i+1}:\n{cleaned_rule}\n{'-'*60}")

# ✅ Final summary
all_docs = collection.get().get("documents", [])
print(f"\n🎯 Total Chunks Stored: {len(all_docs)}")  # type: ignore
for idx, doc in enumerate(all_docs, 1):  # type: ignore
    preview = doc.strip().splitlines()[0][:80]
    print(f"📦 Chunk {idx}: {preview}...")