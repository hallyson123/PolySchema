import re
from typing import Optional, List
from models import Entity, Property, Relationship, KeyConstraint, IntermediateSchema
from .base_parser import SchemaParser
import json

class RedisParser(SchemaParser):
    def parse(self, schema_text: str) -> IntermediateSchema:
        data = json.loads(schema_text)
        schema = IntermediateSchema(name=data.get("title", "RedisSchema"))
        if "properties" not in data: return schema
        for entity_name, entity_schema in data["properties"].items():
            entity = Entity(name=entity_name, entity_type="KEY_VALUE")
            required_fields = set(entity_schema.get("required", []))
            if "properties" in entity_schema:
                for prop_name, prop_schema in entity_schema["properties"].items():
                    prop_type = self._map_type(prop_schema.get("type"))
                    constraints = ["REQUIRED"] if prop_name in required_fields else ["OPTIONAL"]
                    prop = Property(name=prop_name, type=prop_type, constraints=constraints)
                    entity.properties.append(prop)
            schema.entities[entity_name] = entity
        return schema

    def _map_type(self, json_type: str) -> str:
        if not json_type: return "STRING"
        type_map = {"integer": "NUMBER", "number": "NUMBER", "string": "STRING", "boolean": "BOOLEAN", "date-time": "DATE"}
        return type_map.get(json_type.lower(), "STRING")