from models import IntermediateSchema
from generator import SchemaGenerator
from parsers import SchemaParser, GPFuseParser, JFuseParser, RedisParser, RelationalParser

class MapperTool:
    def __init__(self):
        self._parsers = {}
        self._generator = SchemaGenerator()
        self._register_default_parsers()

    def _register_default_parsers(self):
        self.register_parser("gpfuse", GPFuseParser())
        self.register_parser("jfuse", JFuseParser())
        self.register_parser("redis", RedisParser())
        self.register_parser("relational", RelationalParser())

    def register_parser(self, name: str, parser: SchemaParser):
        self._parsers[name] = parser

    def map(self, schema_text: str, parser_name: str) -> IntermediateSchema:
        if parser_name not in self._parsers:
            raise ValueError(f"Parser '{parser_name}' não está registrado.")
        parser = self._parsers[parser_name]
        return parser.parse(schema_text)