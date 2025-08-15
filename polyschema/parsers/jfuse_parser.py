import re
from typing import Optional, List
from models import Entity, Property, Relationship, KeyConstraint, IntermediateSchema
from .base_parser import SchemaParser
from typing import Dict, Optional

class JFuseParser(SchemaParser):
    def parse(self, schema_text: str) -> IntermediateSchema:
        schema = IntermediateSchema(name="JFuseSchema")
        parsed_rules = {}
        rule_pattern = re.compile(r"(\w+)\s*::=\s*(.*)")
        full_text = re.sub(r",\s*\n\s*", ", ", schema_text)
        for line in full_text.split('\n'):
            line = line.strip()
            if not line: continue
            match = rule_pattern.match(line)
            if match:
                lhs, rhs = match.groups()
                parsed_rules[lhs.strip()] = rhs.strip()
        if 'root' not in parsed_rules:
            raise ValueError("Regra 'root' não encontrada no schema JFUSE.")
        root_rhs = parsed_rules['root'].strip('{}')
        for field in root_rhs.split(','):
            if ':' not in field: continue
            entity_name, rule_ref = [x.strip() for x in field.split(':')]
            obj_rule_name = self._resolve_object_rule(rule_ref, parsed_rules)
            if obj_rule_name and obj_rule_name in parsed_rules:
                entity = Entity(name=entity_name, entity_type="DOCUMENT")
                properties, key_constraints = self._build_properties_from_rule(obj_rule_name, parsed_rules)
                entity.properties = properties
                schema.entities[entity.name] = entity
                for kc in key_constraints:
                    kc.entity_name = entity_name
                    kc.constraint_name = f"{entity_name}Key"
                    schema.key_constraints.append(kc)
        return schema

    def _resolve_object_rule(self, rule_name: str, parsed_rules: Dict) -> Optional[str]:
        if rule_name not in parsed_rules: return None
        rhs = parsed_rules[rule_name]
        return rhs.strip('[]') if rhs.startswith('[') and rhs.endswith(']') else rule_name

    def _build_properties_from_rule(self, rule_name: str, parsed_rules: Dict) -> (List[Property], List[KeyConstraint]):
        properties, key_constraints = [], []
        if rule_name not in parsed_rules: return [], []
        rule_body = parsed_rules[rule_name]
        prop_definitions = re.split(r",\s*(?![^[]*\])", rule_body)
        for prop_def in prop_definitions:
            prop_def = prop_def.strip()
            if ':' not in prop_def: continue
            prop_name, type_str = [x.strip() for x in prop_def.split(':', 1)]
            is_key = type_str.endswith('k')
            if is_key: type_str = type_str[:-1]
            prop = Property(name=prop_name, type="STRING")
            if is_key: prop.constraints.append("REQUIRED")
            type_map = {'R': 'NUMBER', 'TS': 'DATE', 'S': 'STRING', 'null': 'NULL'}
            if type_str in type_map:
                prop.type = type_map.get(type_str)
            elif type_str.startswith('[') and type_str.endswith(']'):
                prop.type = 'ENUM'
                values = type_str.strip('[]').replace('...', '').split(',')
                prop.details['values'] = [v.strip() for v in values if v.strip()]
            elif type_str.startswith('arr_'):
                prop.type = 'ARRAY'
                obj_rule_ref = self._resolve_object_rule(type_str, parsed_rules)
                if obj_rule_ref:
                    nested_props, nested_keys = self._build_properties_from_rule(obj_rule_ref, parsed_rules)
                    prop.details['nested_properties'] = nested_props
                    key_prop_names = {p for key in nested_keys for p in key.properties}
                    for p_nested in prop.details['nested_properties']:
                        if p_nested.name in key_prop_names and 'KEY' not in p_nested.constraints:
                             p_nested.constraints.append('KEY')
            if is_key and 'KEY' not in prop.constraints:
                prop.constraints.append("KEY")
                key_constraints.append(KeyConstraint(entity_name="", properties=[prop_name]))
            properties.append(prop)
        return properties, key_constraints