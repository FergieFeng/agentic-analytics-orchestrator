"""
Indexer: Index knowledge base and schema into vector store.

Creates embeddings for:
- Business glossary terms
- Metric definitions
- SQL patterns
- Schema columns and enums
- Business rules
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from src.config.settings import settings
from .vector_store import (
    get_vector_store, 
    KNOWLEDGE_COLLECTION, 
    SCHEMA_COLLECTION
)


def load_knowledge() -> Dict[str, Any]:
    """Load knowledge.json file."""
    knowledge_path = settings.project_root / settings.knowledge_path
    with open(knowledge_path) as f:
        return json.load(f)


def load_schema() -> Dict[str, Any]:
    """Load schema.json file."""
    schema_path = settings.project_root / settings.schema_path
    with open(schema_path) as f:
        return json.load(f)


def chunk_knowledge(knowledge: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Chunk knowledge.json into indexable documents.
    
    Returns:
        List of (text, metadata) tuples
    """
    chunks = []
    
    # 1. Glossary - Products
    for term, definition in knowledge.get("glossary", {}).get("products", {}).items():
        chunks.append((
            f"Product Term: {term}\nDefinition: {definition}",
            {"type": "glossary", "category": "product", "term": term}
        ))
    
    # 2. Glossary - Terms
    for term, definition in knowledge.get("glossary", {}).get("terms", {}).items():
        chunks.append((
            f"Business Term: {term}\nDefinition: {definition}",
            {"type": "glossary", "category": "term", "term": term}
        ))
    
    # 3. Metrics - by category
    for category, metrics in knowledge.get("metrics", {}).items():
        for metric in metrics:
            name = metric.get("name", "")
            definition = metric.get("definition", "")
            sql = metric.get("sql", "")
            chunks.append((
                f"Metric: {name}\nCategory: {category}\nDefinition: {definition}\nSQL Pattern: {sql}",
                {"type": "metric", "category": category, "name": name}
            ))
    
    # 4. SQL Patterns
    for pattern_name, pattern_info in knowledge.get("sql_patterns", {}).items():
        description = pattern_info.get("description", "")
        sql = pattern_info.get("sql", "")
        chunks.append((
            f"SQL Pattern: {pattern_name}\nDescription: {description}\nExample SQL: {sql}",
            {"type": "sql_pattern", "name": pattern_name}
        ))
    
    # 5. Business Rules
    for i, rule in enumerate(knowledge.get("business_rules", [])):
        chunks.append((
            f"Business Rule: {rule}",
            {"type": "business_rule", "index": i}
        ))
    
    # 6. Question Mappings
    for mapping in knowledge.get("question_mapping", []):
        pattern = mapping.get("question_pattern", "")
        filters = mapping.get("key_filters", "")
        agg = mapping.get("aggregation", "")
        chunks.append((
            f"Question Pattern: {pattern}\nKey Filters: {filters or 'None'}\nAggregation: {agg}",
            {"type": "question_mapping", "pattern": pattern}
        ))
    
    return chunks


def chunk_schema(schema: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Chunk schema.json into indexable documents.
    
    Returns:
        List of (text, metadata) tuples
    """
    chunks = []
    
    table_name = schema.get("table_name", "events")
    table_desc = schema.get("description", "")
    
    # 1. Table overview
    chunks.append((
        f"Table: {table_name}\nDescription: {table_desc}",
        {"type": "table_overview", "table": table_name}
    ))
    
    # 2. Query hints
    hints = schema.get("query_hints", {})
    if hints:
        privacy = hints.get("privacy", {})
        cost = hints.get("cost_controls", {})
        chunks.append((
            f"Query Guidelines for {table_name}:\n"
            f"- Default time grain: {hints.get('default_time_grain', 'month')}\n"
            f"- Privacy: k-anonymity minimum {privacy.get('k_anonymity_min_distinct_accounts', 10)} accounts\n"
            f"- No identifiers in output: {privacy.get('no_identifier_output', True)}\n"
            f"- Result row limit: {cost.get('result_row_limit', 200)}",
            {"type": "query_hints", "table": table_name}
        ))
    
    # 3. Columns
    for col in schema.get("columns", []):
        col_name = col.get("name", "")
        col_type = col.get("type", "")
        col_desc = col.get("description", "")
        is_cat = col.get("is_categorical", False)
        enum_vals = col.get("enum", [])
        
        text = f"Column: {col_name}\nType: {col_type}\nDescription: {col_desc}"
        if is_cat:
            text += f"\nCategorical: Yes"
        if enum_vals:
            text += f"\nPossible values: {', '.join(enum_vals)}"
        
        chunks.append((
            text,
            {"type": "column", "column_name": col_name, "column_type": col_type}
        ))
    
    # 4. Enum definitions
    for enum_name, enum_values in schema.get("enums", {}).items():
        if isinstance(enum_values, dict):
            # Enum with descriptions
            for value, desc in enum_values.items():
                chunks.append((
                    f"Enum Value: {enum_name} = '{value}'\nMeaning: {desc}",
                    {"type": "enum", "enum_name": enum_name, "value": value}
                ))
        elif isinstance(enum_values, list):
            # Simple list of values
            chunks.append((
                f"Enum: {enum_name}\nValues: {', '.join(str(v) for v in enum_values)}",
                {"type": "enum", "enum_name": enum_name}
            ))
    
    # 5. Notes
    for i, note in enumerate(schema.get("notes", [])):
        chunks.append((
            f"Schema Note: {note}",
            {"type": "note", "index": i}
        ))
    
    return chunks


def index_knowledge_base(force_reindex: bool = False) -> Dict[str, int]:
    """
    Index knowledge.json and schema.json into ChromaDB.
    
    Args:
        force_reindex: If True, delete existing and re-index
        
    Returns:
        Dict with counts of indexed documents
    """
    store = get_vector_store()
    
    results = {
        "knowledge_chunks": 0,
        "schema_chunks": 0,
        "total": 0
    }
    
    # Check if already indexed
    knowledge_count = store.get_collection_count(KNOWLEDGE_COLLECTION)
    schema_count = store.get_collection_count(SCHEMA_COLLECTION)
    
    if not force_reindex and knowledge_count > 0 and schema_count > 0:
        # Already indexed
        results["knowledge_chunks"] = knowledge_count
        results["schema_chunks"] = schema_count
        results["total"] = knowledge_count + schema_count
        results["status"] = "already_indexed"
        return results
    
    # Delete existing if force reindex
    if force_reindex:
        store.delete_collection(KNOWLEDGE_COLLECTION)
        store.delete_collection(SCHEMA_COLLECTION)
    
    # Load and chunk documents
    knowledge = load_knowledge()
    schema = load_schema()
    
    knowledge_chunks = chunk_knowledge(knowledge)
    schema_chunks = chunk_schema(schema)
    
    # Index knowledge
    if knowledge_chunks:
        documents = [chunk[0] for chunk in knowledge_chunks]
        metadatas = [chunk[1] for chunk in knowledge_chunks]
        ids = [f"knowledge_{i}" for i in range(len(knowledge_chunks))]
        
        store.add_documents(
            collection=KNOWLEDGE_COLLECTION,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        results["knowledge_chunks"] = len(knowledge_chunks)
    
    # Index schema
    if schema_chunks:
        documents = [chunk[0] for chunk in schema_chunks]
        metadatas = [chunk[1] for chunk in schema_chunks]
        ids = [f"schema_{i}" for i in range(len(schema_chunks))]
        
        store.add_documents(
            collection=SCHEMA_COLLECTION,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        results["schema_chunks"] = len(schema_chunks)
    
    results["total"] = results["knowledge_chunks"] + results["schema_chunks"]
    results["status"] = "indexed"
    
    return results


def is_indexed() -> bool:
    """Check if knowledge base is already indexed."""
    store = get_vector_store()
    return (
        store.get_collection_count(KNOWLEDGE_COLLECTION) > 0 and
        store.get_collection_count(SCHEMA_COLLECTION) > 0
    )


def get_index_stats() -> Dict[str, Any]:
    """Get statistics about the indexed documents."""
    store = get_vector_store()
    
    return {
        "knowledge_collection": {
            "count": store.get_collection_count(KNOWLEDGE_COLLECTION)
        },
        "schema_collection": {
            "count": store.get_collection_count(SCHEMA_COLLECTION)
        },
        "collections": store.list_collections()
    }


if __name__ == "__main__":
    # Test indexing
    print("Indexing knowledge base...")
    results = index_knowledge_base(force_reindex=True)
    print(f"Results: {results}")
    
    print("\nIndex stats:")
    stats = get_index_stats()
    print(f"  Knowledge: {stats['knowledge_collection']['count']} chunks")
    print(f"  Schema: {stats['schema_collection']['count']} chunks")
