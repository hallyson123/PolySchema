from abc import ABC, abstractmethod
from models import IntermediateSchema

class SchemaParser(ABC):
    @abstractmethod
    def parse(self, schema_text: str) -> IntermediateSchema:
        pass