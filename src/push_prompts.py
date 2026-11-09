"""
Script para fazer push de prompts otimizados ao LangSmith Prompt Hub.

Este script:
1. Lê os prompts otimizados de prompts/bug_to_user_story_v2.yml
2. Valida os prompts
3. Faz push PÚBLICO para o LangSmith Hub
4. Adiciona metadados (tags, descrição, técnicas utilizadas)

DICAS DE IMPLEMENTAÇÃO:

- O push é feito pelo cliente do LangSmith:

      from langsmith import Client
      from langchain_core.prompts import ChatPromptTemplate

      client = Client()
      prompt = ChatPromptTemplate.from_messages([
          ("system", system_prompt),
          ("user", user_prompt),
      ])
      url = client.push_prompt(
          f"{username}/bug_to_user_story_v2",
          object=prompt,
          is_public=True,
          description="...",
          tags=[...],
      )

- `username` vem de USERNAME_LANGSMITH_HUB no .env e precisa ser o seu handle
  do Hub. Se você ainda não tem um handle, veja as instruções no .env.example.

- A variável do template precisa ser {bug_report}, que é a chave de entrada
  usada no dataset de avaliação.

- Use `load_yaml` de utils.py para ler o arquivo .yml.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from langsmith import Client
from langchain_core.prompts import ChatPromptTemplate

from utils import load_yaml, check_env_vars, print_section_header, validate_prompt_structure

load_dotenv()

# Arquivo local do prompt otimizado (fonte da verdade local)
PROMPT_FILE = Path(__file__).resolve().parent.parent / "prompts" / "bug_to_user_story_v2.yml"

# Chave do prompt dentro do YAML (o arquivo tem um dict com essa chave na raiz)
PROMPT_KEY = "bug_to_user_story_v2"


def push_prompt_to_langsmith(prompt_name: str, prompt_data: dict) -> bool:
    """
    Faz push do prompt otimizado para o LangSmith Hub (PÚBLICO).

    Args:
        prompt_name: Nome do prompt
        prompt_data: Dados do prompt

    Returns:
        True se sucesso, False caso contrário
    """
    try:
        system_prompt = prompt_data["system_prompt"]
        user_prompt = prompt_data["user_prompt"]

        # Monta o objeto que será publicado no Hub.
        # É o mesmo formato que o evaluate.py espera puxar:
        # um ChatPromptTemplate com mensagem de system + mensagem de usuário.
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", user_prompt),
        ])

        # Guarda de segurança: o evaluate.py invoca a chain apenas com
        # {"bug_report": ...}. Se o template tiver qualquer outra variável
        # (ex: um {chave} indevido no system_prompt), a avaliação falharia
        # com "Missing some input keys".
        if prompt.input_variables != ["bug_report"]:
            print(
                f"❌ Variáveis inesperadas no template: {prompt.input_variables}\n"
                "   Esperado apenas ['bug_report'].\n"
                "   Remova qualquer {chave} indevida do YAML (use [colchetes] para placeholders)."
            )
            return False

        client = Client()

        print(f"   Enviando prompt para o LangSmith Hub: {prompt_name}")
        url = client.push_prompt(
            prompt_name,
            object=prompt,
            is_public=True,
            description=prompt_data.get("description", ""),
            tags=prompt_data.get("tags", []),
        )

        print(f"   ✓ Prompt publicado com sucesso")
        print(f"   ✓ {url}")
        return True

    except Exception as e:
        print(f"   ❌ Falha ao fazer push do prompt: {e}")
        print("\n   Verifique:")
        print("   - LANGSMITH_API_KEY está configurada no .env")
        print("   - USERNAME_LANGSMITH_HUB é o seu handle do Hub (definido no Make Public)")
        print("   - Você tem conexão com a internet")
        return False


def validate_prompt(prompt_data: dict) -> tuple[bool, list]:
    """
    Valida estrutura básica de um prompt (versão simplificada).

    Args:
        prompt_data: Dados do prompt

    Returns:
        (is_valid, errors) - Tupla com status e lista de erros
    """
    # Reaproveita a validação oficial da utils.py:
    # checa description/system_prompt/version, system_prompt sem TODO
    # e pelo menos 2 técnicas em techniques_applied.
    is_valid, errors = validate_prompt_structure(prompt_data)

    # Checagens extras específicas do push:
    user_prompt = prompt_data.get("user_prompt", "")
    if not user_prompt.strip():
        errors.append("user_prompt está vazio")
    elif "{bug_report}" not in user_prompt:
        errors.append(
            "user_prompt deve conter a variável {bug_report} "
            "(chave de entrada do dataset de avaliação)"
        )

    return (len(errors) == 0, errors)


def main():
    """Função principal"""
    print_section_header("PUSH DE PROMPTS - LANGSMITH PROMPT HUB")

    if not check_env_vars(["LANGSMITH_API_KEY", "USERNAME_LANGSMITH_HUB"]):
        return 1

    # 1. Carrega o YAML local
    data = load_yaml(str(PROMPT_FILE))
    if data is None:
        return 1

    if PROMPT_KEY not in data:
        print(f"❌ Chave '{PROMPT_KEY}' não encontrada em {PROMPT_FILE}")
        return 1

    prompt_data = data[PROMPT_KEY]

    # 2. Valida a estrutura antes de enviar
    print("Validando estrutura do prompt...")
    is_valid, errors = validate_prompt(prompt_data)

    if not is_valid:
        print("   ❌ Prompt inválido:")
        for error in errors:
            print(f"      - {error}")
        return 1

    print("   ✓ Estrutura válida")

    # 3. Faz push para o Hub
    username = os.getenv("USERNAME_LANGSMITH_HUB")
    prompt_name = f"{username}/{PROMPT_KEY}"
    print()

    if push_prompt_to_langsmith(prompt_name, prompt_data):
        print("\n✅ Push concluído com sucesso!")
        print(f"\nPróximo passo: rodar a avaliação")
        print("   venv/bin/python src/evaluate.py")
        return 0

    print("\n❌ Push não concluído. Corrija os erros acima e tente novamente.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
