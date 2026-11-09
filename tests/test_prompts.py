"""
Testes automatizados para validação de prompts.

Valida o prompt otimizado (prompts/bug_to_user_story_v2.yml) quanto aos
requisitos do desafio:
  - system_prompt presente e não vazio
  - persona definida (Role Prompting)
  - formato de saída exigido (Markdown / User Story padrão)
  - exemplos de entrada/saída (Few-shot Learning)
  - ausência de [TODO] esquecido
  - pelo menos 2 técnicas nos metadados

Executar com: pytest tests/test_prompts.py -v
"""
import re
import sys
import yaml
from pathlib import Path

import pytest

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils import validate_prompt_structure

# Caminho do prompt otimizado (o arquivo validado pela entrega)
PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "bug_to_user_story_v2.yml"
PROMPT_KEY = "bug_to_user_story_v2"


def load_prompts(file_path: str):
    """Carrega prompts do arquivo YAML."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def get_prompt() -> dict:
    """
    Carrega o YAML e retorna apenas o prompt da chave bug_to_user_story_v2,
    com mensagens de erro claras caso a estrutura esteja inesperada.
    """
    assert PROMPT_FILE.exists(), f"Arquivo não encontrado: {PROMPT_FILE}"

    data = load_prompts(str(PROMPT_FILE))
    assert data is not None, f"YAML inválido ou não parseável: {PROMPT_FILE}"
    assert PROMPT_KEY in data, f"Chave '{PROMPT_KEY}' ausente no YAML"

    return data[PROMPT_KEY]


class TestPrompts:
    def test_prompt_has_system_prompt(self):
        """Verifica se o campo 'system_prompt' existe e não está vazio."""
        prompt = get_prompt()

        assert "system_prompt" in prompt, "Campo 'system_prompt' ausente no YAML"
        assert prompt["system_prompt"].strip(), "Campo 'system_prompt' está vazio"

    def test_prompt_has_role_definition(self):
        """Verifica se o prompt define uma persona (ex: "Você é um Product Manager")."""
        system_prompt = get_prompt()["system_prompt"]

        # Role Prompting: o prompt deve abrir com uma persona explícita
        assert re.search(
            r"você é um product manager",
            system_prompt,
            flags=re.IGNORECASE,
        ), "Persona 'Você é um Product Manager' não encontrada no system_prompt"

    def test_prompt_mentions_format(self):
        """Verifica se o prompt exige formato Markdown ou User Story padrão."""
        system_prompt = get_prompt()["system_prompt"].lower()

        mentions_markdown = "markdown" in system_prompt
        mentions_story_format = (
            "como um" in system_prompt
            and "eu quero" in system_prompt
            and "para que" in system_prompt
        )

        assert mentions_markdown or mentions_story_format, (
            "O prompt não exige formato de saída "
            "(Markdown ou template 'Como um... eu quero... para que...')"
        )

    def test_prompt_has_few_shot_examples(self):
        """Verifica se o prompt contém exemplos de entrada/saída (técnica Few-shot)."""
        system_prompt = get_prompt()["system_prompt"].lower()

        # Few-shot Learning: 2-3 exemplos completos de entrada -> saída
        count_entradas = system_prompt.count("**entrada:**")
        count_saidas = system_prompt.count("**saída:**")

        assert "exemplo" in system_prompt, "Seção de exemplos não encontrada"
        assert count_entradas >= 2, (
            f"Few-shot exige 2+ exemplos; encontrados: {count_entradas} '**Entrada:**'"
        )
        assert count_saidas >= 2, (
            f"Few-shot exige 2+ exemplos; encontrados: {count_saidas} '**Saída:**'"
        )

    def test_prompt_no_todos(self):
        """Garante que você não esqueceu nenhum `[TODO]` no texto."""
        prompt = get_prompt()

        campos = {
            "system_prompt": prompt.get("system_prompt", ""),
            "user_prompt": prompt.get("user_prompt", ""),
        }

        for nome, texto in campos.items():
            assert "TODO" not in texto, (
                f"Campo '{nome}' ainda contém um [TODO] não preenchido"
            )

    def test_minimum_techniques(self):
        """Verifica (através dos metadados do yaml) se pelo menos 2 técnicas foram listadas."""
        prompt = get_prompt()

        techniques = prompt.get("techniques_applied", [])
        assert isinstance(techniques, list), "'techniques_applied' deve ser uma lista"
        assert len(techniques) >= 2, (
            f"Mínimo de 2 técnicas requeridas nos metadados; encontradas: {len(techniques)}"
        )


class TestExtra:
    """Testes adicionais (além dos 6 obrigatórios) que protegem contra bugs conhecidos."""

    def test_validate_prompt_structure(self):
        """Reaproveita a validação oficial da utils.py (estrutura + técnicas + sem TODO)."""
        is_valid, errors = validate_prompt_structure(get_prompt())
        assert is_valid, f"validate_prompt_structure falhou: {errors}"

    def test_user_prompt_uses_bug_report_variable(self):
        """O user_prompt deve usar exatamente a variável {bug_report} do dataset."""
        user_prompt = get_prompt()["user_prompt"]

        assert user_prompt == "{bug_report}", (
            f"user_prompt deve ser '{{bug_report}}'; encontrado: {user_prompt!r}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
