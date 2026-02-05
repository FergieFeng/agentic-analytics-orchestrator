"""
Index Builder: Build retrieval index from schema and docs.

Note: This is a lightweight implementation for Phase 1.
Full vector search will be implemented in Phase 3.
"""

from typing import List, Dict
import json


def build_index(schema_path: str = "src/config/schema.json") -> List[Dict]:
    """
    Build a simple retrieval index from schema.
    
    Args:
        schema_path: Path to schema.json
        
    Returns:
        List of indexed documents
    """
    
    # TODO: Implement index building
    # 1. Load schema.json
    # 2. Create searchable documents
    # 3. Optionally compute embeddings (Phase 3)
    
    documents = []
    
    try:
        with open(schema_path, "r") as f:
            schema = json.load(f)
            
        # Index each column as a document
        for column in schema.get("columns", []):
            documents.append({
                "id": column["name"],
                "type": "column",
                "content": f"{column['name']}: {column.get('description', '')}",
                "metadata": column
            })
            
    except FileNotFoundError:
        print(f"Schema file not found: {schema_path}")
    
    return documents


if __name__ == "__main__":
    docs = build_index()
    print(f"Indexed {len(docs)} documents")
