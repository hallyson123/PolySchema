import re
from typing import Optional, List
from models import Entity, Property, Relationship, KeyConstraint, IntermediateSchema
from .base_parser import SchemaParser

class RelationalParser(SchemaParser):
    def parse(self, schema_text: str) -> IntermediateSchema:
        schema = IntermediateSchema(name="RelationalSchema")
        create_table_blocks = re.findall(r"CREATE TABLE.*?;", schema_text, re.DOTALL | re.IGNORECASE)
        for block in create_table_blocks:
            entity, key_constraint = self._parse_entity_and_pk(block)
            if entity: schema.entities[entity.name] = entity
            if key_constraint: schema.key_constraints.append(key_constraint)
        for block in create_table_blocks:
            relationships = self._parse_relationships(block)
            schema.relationships.extend(relationships)
        return schema
    def _parse_entity_and_pk(self, block: str):
        table_name_match = re.search(r"CREATE TABLE\s+([`\"\w]+)", block, re.IGNORECASE)
        if not table_name_match: return None, None
        entity_name = table_name_match.group(1).strip('`"')
        entity = Entity(name=entity_name, entity_type="RELATIONAL")
        content_match = re.search(r"\((.*)\)", block, re.DOTALL)
        if not content_match: return entity, None
        content = content_match.group(1)
        definitions = self._split_definitions(content)
        pk_columns = set()
        key_constraint_obj = None
        for def_line in definitions:
            pk_match = re.search(r"PRIMARY KEY\s*\((.*?)\)", def_line, re.IGNORECASE)
            if pk_match:
                pk_cols_str = pk_match.group(1)
                pk_columns.update([col.strip().strip('`"') for col in pk_cols_str.split(',')])
                constraint_name_match = re.search(r"CONSTRAINT\s+([`\"\w]+)", def_line, re.IGNORECASE)
                constraint_name = constraint_name_match.group(1).strip('`"') if constraint_name_match else f"{entity_name}Key"
                key_constraint_obj = KeyConstraint(entity_name=entity_name, properties=list(pk_columns), constraint_name=constraint_name)
                break
        for def_line in definitions:
            def_line = def_line.strip()
            if def_line.upper().startswith("CONSTRAINT") or not def_line: continue
            parts = def_line.split()
            prop_name = parts[0].strip('`"')
            sql_type = parts[1]
            is_inline_pk = "PRIMARY KEY" in def_line.upper()
            if is_inline_pk and not pk_columns:
                pk_columns.add(prop_name)
                key_constraint_obj = KeyConstraint(entity_name=entity_name, properties=[prop_name], constraint_name=f"{entity_name}Key")
            prop = Property(name=prop_name, type=self._map_type(sql_type))
            prop.constraints.append("REQUIRED" if "NOT NULL" in def_line.upper() else "OPTIONAL")
            if prop_name in pk_columns: prop.constraints.append("KEY")
            entity.properties.append(prop)
        return entity, key_constraint_obj
    def _parse_relationships(self, block: str) -> List[Relationship]:
        relationships = []
        table_name_match = re.search(r"CREATE TABLE\s+([`\"\w]+)", block, re.IGNORECASE)
        if not table_name_match: return []
        source_entity_name = table_name_match.group(1).strip('`"')
        fk_matches = re.finditer(r"CONSTRAINT\s+([`\"\w]+)\s+FOREIGN KEY\s*\((.*?)\)\s+REFERENCES\s+([`\"\w]+)", block, re.IGNORECASE)
        for match in fk_matches:
            rel = Relationship(name=match.group(1).strip('`"'), source_entity=source_entity_name, target_entity=match.group(3).strip('`"'), cardinality_fwd="1:1", cardinality_bwd="0:N")
            relationships.append(rel)
        return relationships
    def _split_definitions(self, content: str) -> List[str]:
        definitions = []
        balance = 0
        last_split = 0
        for i, char in enumerate(content):
            if char == '(': balance += 1
            elif char == ')': balance -= 1
            elif char == ',' and balance == 0:
                definitions.append(content[last_split:i].strip())
                last_split = i + 1
        definitions.append(content[last_split:].strip())
        return [d for d in definitions if d]
    def _map_type(self, sql_type: str) -> str:
        sql_type_upper = sql_type.upper()
        if any(t in sql_type_upper for t in ["INT", "REAL", "SMALLINT"]): return "NUMBER"
        if any(t in sql_type_upper for t in ["CHAR", "TEXT"]): return "STRING"
        if any(t in sql_type_upper for t in ["DATE", "TIMESTAMP"]): return "DATE"
        return "STRING"