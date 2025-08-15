import os
import re
from tool import MapperTool
from generator import SchemaGenerator

if __name__ == "__main__":
    INPUT_DIR, OUTPUT_DIR = "schemas", "result"
    os.makedirs(INPUT_DIR, exist_ok=True); os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Etapa 1: Mapeamento individual (gera arquivos na pasta result)
    tool = MapperTool()
    generator = SchemaGenerator()
    
    files_to_process = [f for f in os.listdir(INPUT_DIR) if f.endswith(".txt")]
    
    if not files_to_process:
        print(f"Aviso: A pasta '{INPUT_DIR}' está vazia ou não contém arquivos .txt.")
    else:
        print("--- Fase 1: Mapeamento Individual ---")
        for filename in files_to_process:
            input_path = os.path.join(INPUT_DIR, filename)
            output_path = os.path.join(OUTPUT_DIR, filename)
            
            parser_to_use = "gpfuse"
            if "jfuse" in filename.lower(): parser_to_use = "jfuse"
            elif "redis" in filename.lower(): parser_to_use = "redis"
            elif "relational" in filename.lower(): parser_to_use = "relational"
            
            print(f"Processando '{input_path}' usando o parser '{parser_to_use}'...")
            try:
                with open(input_path, 'r', encoding='utf-8') as f: schema_text = f.read()
                intermediate_schema = tool.map(schema_text, parser_to_use)
                final_schema_str = generator.generate(intermediate_schema)
                with open(output_path, 'w', encoding='utf-8') as f: f.write(final_schema_str)
                print(f"Mapeamento concluído. Resultado salvo em '{output_path}'.\n")
            except Exception as e:
                print(f"ERRO ao processar o arquivo {filename}: {e}\n")

    # Etapa 2: Unificação dos schemas da pasta result/
    print("--- Fase 2: Unificação dos Schemas ---")
    
    unified_filename = "unified_schema.txt"
    all_definitions = []
    
    result_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith(".txt") and f != unified_filename]

    if not result_files:
        print(f"Nenhum arquivo encontrado em '{OUTPUT_DIR}' para unificar.")
    else:
        print(f"Unificando {len(result_files)} arquivo(s) de '{OUTPUT_DIR}'...")
        for filename in result_files:
            filepath = os.path.join(OUTPUT_DIR, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                inner_content_match = re.search(r"SCHEMA\s+.*?\{(.*)\}", content, re.DOTALL)
                
                if inner_content_match:
                    inner_content = inner_content_match.group(1).strip()
                    all_definitions.append('\t' + inner_content)
        
        # Monta o arquivo final
        unified_content = "\n\n".join(all_definitions)
        final_output_str = f"SCHEMA UnifiedPolySchema {{\n{unified_content}\n}}"
        
        unified_output_path = os.path.join(OUTPUT_DIR, unified_filename)
        try:
            with open(unified_output_path, 'w', encoding='utf-8') as f:
                f.write(final_output_str)
            print(f"Unificação concluída. Resultado salvo em '{unified_output_path}'.\n")
        except Exception as e:
            print(f"ERRO ao salvar o arquivo unificado: {e}")

    print("Processamento de todos os arquivos concluído.")