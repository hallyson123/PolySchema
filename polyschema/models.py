from dataclasses import dataclass, field
from typing import List, Optional, Dict

@dataclass
class Property:
    name: str
    type: str
    constraints: List[str] = field(default_factory=list)
    details: Dict = field(default_factory=dict)

@dataclass
class Entity:
    name: str
    entity_type: str = "RELATIONAL"
    properties: List[Property] = field(default_factory=list)
    extends: Optional[str] = None
    original_type_name: Optional[str] = None

@dataclass
class Relationship:
    name: str
    source_entity: str
    target_entity: str
    cardinality_fwd: str
    cardinality_bwd: str
    properties: List[Property] = field(default_factory=list)

@dataclass
class KeyConstraint:
    entity_name: str
    properties: List[str]
    constraint_name: Optional[str] = None
    
@dataclass
class IntermediateSchema:
    name: str = "UnnamedSchema"
    entities: Dict[str, Entity] = field(default_factory=dict)
    relationships: List[Relationship] = field(default_factory=list)
    key_constraints: List[KeyConstraint] = field(default_factory=list)