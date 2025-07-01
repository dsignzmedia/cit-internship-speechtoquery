from openai import OpenAI
import os
from dotenv import load_dotenv
from typing import Dict, Any
from datetime import datetime
import re
import chromadb
from chromadb.utils import embedding_functions

# Get the current year
current_year = datetime.now().year

def clean_sql_response(raw_sql: str) -> str:
    match = re.search(r"```(?:sql)?\s*(.*?)\s*```", raw_sql, re.DOTALL)
    sql = match.group(1).strip() if match else raw_sql.strip()
    sql = sql.replace("\\n", "\n").replace("\\t", "\t").replace('\\"', '"')
    sql = sql.encode('utf-8').decode('unicode_escape')
    return sql

class SQLGenerator:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in .env file")

        self.client = OpenAI(api_key=self.api_key)
        self.model_name = "gpt-3.5-turbo"

        self.chroma_client = chromadb.PersistentClient(path="./chroma_db")
        self.embedding_fn = embedding_functions.OpenAIEmbeddingFunction(
            api_key=self.api_key,
            model_name="text-embedding-3-small"
        )
        self.collection = self.chroma_client.get_or_create_collection(
            name="sql_schema_chunks",
            embedding_function=self.embedding_fn  # type: ignore
        )

    def fetch_relevant_chunks(self, query: str, n_results: int = 20, max_token_limit: int = 700, max_tables: int = 5) -> str:
        result = self.collection.query(
            query_texts=[query],
            n_results=n_results,
        )

        documents = result.get("documents", [[]])[0]  # type: ignore
        metadatas = result.get("metadatas", [[]])[0]  # type: ignore
        distances = result.get("distances", [[]])[0]  # type: ignore

        rule_chunks, relationship_chunks, table_chunks = [], [], []
        used_tables = []

        for doc, meta, dist in zip(documents, metadatas, distances):
            doc_str = str(doc).strip()
            if not doc_str:
                continue

            type_info = meta.get("type") if isinstance(meta, dict) else "unknown"
            print(f"🔎 Distance: {dist:.3f} | Type: {type_info}")

            if type_info == "rule":
                rule_chunks.append((dist, doc_str))
            elif type_info == "schema_relationships":
                relationship_chunks.append((dist, doc_str))
            elif doc_str.startswith("Table:"):
                table_chunks.append((dist, doc_str))
                match = re.match(r"Table:\s*([a-zA-Z0-9_]+)", doc_str)
                if match:
                    used_tables.append(match.group(1))

        relationship_chunks.sort(key=lambda x: x[0])
        rule_chunks.sort(key=lambda x: x[0])
        table_chunks.sort(key=lambda x: x[0])

        top_relationship = [c[1] for c in relationship_chunks[:1]]
        top_rules = [c[1] for c in rule_chunks[:2]]
        top_tables = [c[1] for c in table_chunks[:max_tables]]

        selected_chunks = top_rules + top_relationship + top_tables

        print(f"\n📌 Used Tables: {', '.join(sorted(set(used_tables[:max_tables])))}")
        print(f"📄 Found {len(table_chunks)} table chunks, using top {len(top_tables)}")
        print(f"📦 Selected {len(selected_chunks)} total chunks for prompt.\n")

        total_tokens = 0
        limited_chunks = []

        for i, chunk in enumerate(selected_chunks, 1):
            est_tokens = len(chunk.split()) * 1.25
            if total_tokens + est_tokens > max_token_limit:
                break
            limited_chunks.append(chunk)
            total_tokens += est_tokens

            print(f"Chunk {i} estimated tokens: {est_tokens:.1f}")
            print(f"Chunk {i} preview: {chunk[:200]}...\n")

        return "\n\n".join(limited_chunks)

    def generate_query(self, text_input: str) -> Dict[str, Any]:
        try:
            schema_context = self.fetch_relevant_chunks(text_input)

            user_prompt = f"""You are an expert in writing MySQL queries.

Based on the following schema and rules:
{schema_context}

Write a correct, optimized SQL query for:
\"{text_input}\"



Only return the SQL query, no explanation. End with a semicolon.
"""

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are an expert SQL assistant."},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=300,
                stream=False,
                extra_headers={"OpenAI-Beta": "assistants=v1"},
            )

            print("Prompt tokens:", response.usage.prompt_tokens)  # type: ignore
            print("Completion tokens:", response.usage.completion_tokens)  # type: ignore
            print("Total tokens:", response.usage.total_tokens)  # type: ignore

            sql_query = response.choices[0].message.content.strip()  # type: ignore
            cleaned_query = clean_sql_response(sql_query)

            return {
                "success": True,
                "query": cleaned_query,
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Error generating SQL query: {str(e)}",
                "timestamp": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            }
