import re
from typing import Optional, List
from models import Entity, Property, Relationship, KeyConstraint, IntermediateSchema
from .base_parser import SchemaParser

class GPFuseParser(SchemaParser):
    def parse(self, schema_text: str) -> IntermediateSchema:
        schema_name_match = re.search(r"CREATE GRAPH TYPE (\w+)", schema_text)
        schema_name = schema_name_match.group(1) if schema_name_match else "UnnamedSchema"
        schema = IntermediateSchema(name=schema_name)
        content_match = re.search(r"\{(.*)\}", schema_text, re.DOTALL)
        if not content_match: return schema
        content = content_match.group(1)
        entity_pattern = re.compile(r"\(([\w\s&:]+?\{.*?\})\)", re.DOTALL)
        for match in entity_pattern.finditer(content):
            entity = self._parse_entity(match.group(1))
            if entity: schema.entities[entity.name] = entity
        type_to_entity_name = {e.original_type_name: e.name for e in schema.entities.values()}
        name_resolver = {**type_to_entity_name, **{v: v for v in type_to_entity_name.values()}}
        rel_pattern = re.compile(r"\(:(\w+)\)\s*-\s*\[(.*?)]\s*->\s*\(:(\w+)\)")
        for match in rel_pattern.finditer(content):
            source_type, rel_content, target_type = match.groups()
            source_entity = name_resolver.get(source_type); target_entity = name_resolver.get(target_type)
            if source_entity and target_entity:
                rel = self._parse_relationship(rel_content, source_entity, target_entity)
                schema.relationships.append(rel)
        key_pattern = re.compile(r"FOR\s+\(x:\s*(\w+)\)\s+EXCLUSIVE\s+MANDATORY\s+SINGLETON\s+x\.(\w+|\([^)]+\))")
        for match in key_pattern.finditer(content):
            entity_type, prop_names_str = match.groups()
            entity_name = name_resolver.get(entity_type)
            if entity_name:
                cleaned_props = prop_names_str.strip().strip('()')
                properties_list = [p.strip() for p in cleaned_props.split(',') if p.strip()]
                key = KeyConstraint(entity_name=entity_name, properties=properties_list, constraint_name=f"{entity_name}Key")
                schema.key_constraints.append(key)
        return schema
    def _parse_entity(self, entity_text: str) -> Optional[Entity]:
        header_match = re.match(r"(\w+)\s*:\s*([\w\s&]+?)\s*\{(.*)\}", entity_text, re.DOTALL)
        if not header_match:
            print(f"\nAVISO: Bloco de entidade malformado ignorado:\n{entity_text}\n")
            return None
        original_type, name_part, props_part = header_match.groups()
        extends = None
        if "&" in name_part:
            super_label, sub_label = [n.strip() for n in name_part.split("&")]
            name = sub_label; extends = super_label
        else: name = name_part.strip()
        properties = self._parse_properties(props_part)
        return Entity(name=name, entity_type="GRAPH", properties=properties, extends=extends, original_type_name=original_type)
    def _parse_properties(self, props_text: str) -> List[Property]:
        properties = []
        prop_lines = [p.strip() for p in re.split(r",\s*(?![^()]*\))", props_text) if p.strip()]
        for line in prop_lines:
            is_optional = "OPTIONAL" in line
            cleaned_line = line.replace("OPTIONAL", "").strip()
            constraints = ["OPTIONAL" if is_optional else "REQUIRED"]
            prop_match = re.match(r"(\w+)\s+(.*)", cleaned_line, re.IGNORECASE)
            if not prop_match: continue
            prop_name, prop_type_str = prop_match.groups()
            final_type, details = "", {}
            if "ENUM" in prop_type_str.upper():
                final_type = "ENUM"
                details['values'] = re.findall(r'"(.*?)"', prop_type_str)
            elif "ARRAY" in prop_type_str.upper():
                final_type = "ARRAY"
                type_match = re.search(r"ARRAY\s+(\w+)", prop_type_str, re.IGNORECASE)
                size_match = re.search(r"\((\d+)[,:](\d+)\)", prop_type_str)
                details['inner_type'] = self._map_type(type_match.group(1)) if type_match else "STRING"
                details['min'] = size_match.group(1) if size_match else "0"
                details['max'] = size_match.group(2) if size_match else "N"
            else: final_type = self._map_type(prop_type_str)
            prop = Property(name=prop_name, type=final_type, constraints=constraints, details=details)
            properties.append(prop)
        return properties
    def _parse_relationship(self, rel_text: str, source: str, target: str) -> Relationship:
        temp_rel_text = rel_text
        card_match = re.search(r"\(([\d\w:]+)\)\s*;\s*\(([\d\w:]+)\)", temp_rel_text)
        bwd, fwd = card_match.groups() if card_match else ("0:N", "0:N")
        if card_match:
            temp_rel_text = temp_rel_text.replace(card_match.group(0), "").strip()
        props_part_match = re.search(r"\((.*)\)", temp_rel_text)
        props_str = props_part_match.group(1) if props_part_match else ""
        name_match = re.match(r"\w+\s*:\s*(\w+)", temp_rel_text)
        rel_name = name_match.group(1) if name_match else "RELATED_TO"
        properties = self._parse_properties(props_str) if props_str else []
        return Relationship(name=rel_name, source_entity=source, target_entity=target,cardinality_fwd=fwd.strip(), cardinality_bwd=bwd.strip(),properties=properties)
    def _map_type(self, gpfuse_type: str) -> str:
        gpfuse_type = gpfuse_type.upper().strip()
        if gpfuse_type in ["INT", "FLOAT"]: return "NUMBER"
        if gpfuse_type == "STR": return "STRING"
        return gpfuse_type