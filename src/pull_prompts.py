"""
Script para fazer pull de prompts do LangSmith Prompt Hub.

Este script:
1. Conecta ao LangSmith usando credenciais do .env
2. Faz pull do prompt semente (leonanluppi/bug_to_user_story_v1)
3. Salva localmente em prompts/bug_to_user_story_v1.yml
"""

import sys
from pathlib import Path

from dotenv import load_dotenv
from langsmith import Client

from utils import save_yaml, check_env_vars, print_section_header

load_dotenv()

# Prompt semente do desafio (publicado pelo autor do desafio no Hub)
SEED_PROMPT_NAME = "leonanluppi/bug_to_user_story_v1"

# Caminho local de saída (relativo a este arquivo, funciona de qualquer diretório)
OUTPUT_FILE = Path(__file__).resolve().parent.parent / "prompts" / "bug_to_user_story_v1.yml"


def extract_message_text(message) -> str:
    """
    Extrai o texto de template de uma mensagem de um ChatPromptTemplate.

    Mensagens de template (SystemMessagePromptTemplate, HumanMessagePromptTemplate)
    guardam o texto original em message.prompt.template. Se a mensagem já vier
    formatada (conteúdo direto), usamos .content como fallback.
    """
    template_obj = getattr(message, "prompt", None)
    if template_obj is not None and hasattr(template_obj, "template"):
        return template_obj.template

    return str(getattr(message, "content", ""))


def pull_prompts_from_langsmith() -> bool:
    """
    Faz pull do prompt semente do Hub e grava em prompts/bug_to_user_story_v1.yml.

    Returns:
        True se o pull e a gravação derem certo, False caso contrário.
    """
    try:
        client = Client()

        print(f"   Puxando prompt do LangSmith Hub: {SEED_PROMPT_NAME}")
        prompt = client.pull_prompt(
            SEED_PROMPT_NAME,
            dangerously_pull_public_prompt=True,
        )

        # Separa as mensagens do template em system e user
        system_text = ""
        user_text = ""
        for message in prompt.messages:
            text = extract_message_text(message)
            class_name = message.__class__.__name__

            if "System" in class_name:
                system_text = text
            elif "Human" in class_name or "User" in class_name:
                user_text = text

        if not system_text.strip():
            print("   ❌ Prompt recebido não contém mensagem de system.")
            return False

        # Monta o dicionário no mesmo formato do arquivo local de referência.
        # Metadados fixos: o objeto retornado pelo pull é só o template —
        # description/tags do Hub não vêm junto.
        prompt_data = {
            "bug_to_user_story_v1": {
                "description": "Prompt para converter relatos de bugs em User Stories",
                "system_prompt": system_text,
                "user_prompt": user_text,
                "version": "v1",
                "created_at": "2025-01-15",
                "tags": ["bug-analysis", "user-story", "product-management"],
            }
        }

        if save_yaml(prompt_data, str(OUTPUT_FILE)):
            print(f"   ✓ Prompt salvo localmente: {OUTPUT_FILE}")
            return True

        return False

    except Exception as e:
        print(f"   ❌ Falha ao puxar o prompt: {e}")
        print("\n   Verifique:")
        print("   - LANGSMITH_API_KEY está configurada no .env")
        print("   - Você tem conexão com a internet")
        print(f"   - O prompt '{SEED_PROMPT_NAME}' continua público no Hub")
        return False


def main():
    """Função principal"""
    print_section_header("PULL DE PROMPTS - LANGSMITH PROMPT HUB")

    if not check_env_vars(["LANGSMITH_API_KEY"]):
        return 1

    print("Conectando ao LangSmith...")
    print()

    if pull_prompts_from_langsmith():
        print("\n✅ Pull concluído com sucesso!")
        print("\nPróximo passo: analisar o prompt baixado e criar a versão otimizada")
        print("em prompts/bug_to_user_story_v2.yml")
        return 0

    print("\n❌ Pull não concluído. Corrija os erros acima e tente novamente.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
