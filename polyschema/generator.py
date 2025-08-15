from models import IntermediateSchema, Entity, Property, Relationship, KeyConstraint

class SchemaGenerator:
    def generate(self, schema: IntermediateSchema) -> str:
        output = [f"SCHEMA {schema.name} {{\n"]
        for entity in schema.entities.values(): output.append(self._generate_entity(entity))
        for rel in schema.relationships: output.append(self._generate_relationship(rel, schema))
        for key in schema.key_constraints: output.append(self._generate_key_constraint(key))
        output.append("}")
        return "".join(output)
    def _generate_entity(self, entity: Entity) -> str:
        header = f'\tENTITY {entity.name}'
        if entity.extends: header += f' EXTENDS {entity.extends}'
        body = [header + " {\n"]
        body.append(f'\t\t{entity.entity_type.upper()} {{\n')
        if not entity.properties:
            body.append('\n')
        else:
            for prop in entity.properties:
                body.append(self._generate_property(prop, indent_level=3))
        body.append(f'\t\t}}\n')
        body.append("\t}\n")
        return "".join(body)
    def _generate_property(self, prop: Property, indent_level: int = 2) -> str:
        indent = '\t' * indent_level
        type_str = prop.type
        constraints_list = prop.constraints
        if prop.type == "ENUM":
            values = '", "'.join(prop.details.get('values', []))
            type_str = f'ENUM ["{values}"]'
        elif prop.type == "ARRAY":
            if 'nested_properties' in prop.details:
                nested_props_str = "".join([self._generate_property(p, indent_level + 1) for p in prop.details['nested_properties']])
                type_str = f"ARRAY [\n{indent}\tOBJECT {{\n{nested_props_str}{indent}\t}}\n{indent}]"
            else:
                type_str = f"ARRAY [ STRING ]"
        constraints = ", ".join(constraints_list) if constraints_list else ""
        return f'{indent}{prop.name}: {type_str} {{ {constraints} }}\n' if constraints else f'{indent}{prop.name}: {type_str}\n'
    def _generate_relationship(self, rel: Relationship, schema: IntermediateSchema) -> str:
        base_rel_str = (f"\tRELATION {rel.name} " f"FROM {rel.source_entity} TO {rel.target_entity}")
        source_entity_obj = schema.entities.get(rel.source_entity)
        if source_entity_obj and source_entity_obj.entity_type != "RELATIONAL":
            base_rel_str += f" ({rel.cardinality_fwd}) ; ({rel.cardinality_bwd})"
        if not rel.properties: return base_rel_str + "\n"
        body = [" {\n"]
        for prop in rel.properties:
            body.append(self._generate_property(prop, indent_level=2))
        body.append("\t}\n")
        return base_rel_str + "".join(body)
    def _generate_key_constraint(self, key: KeyConstraint) -> str:
        props_str = key.properties[0] if len(key.properties) == 1 else f"({', '.join(key.properties)})"
        return f"\tCONSTRAINT {key.constraint_name} ON {key.entity_name}.{props_str} IS KEY\n"