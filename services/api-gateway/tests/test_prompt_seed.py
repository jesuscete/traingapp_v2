from app.analytics.discipline_seed import DISCIPLINE_SEED
from app.analytics.prompt_seed import (
    DISCIPLINE_PROMPT_SEED,
    TRAINING_PROMPT_SEED,
)

_PLACEHOLDERS = (
    "{deportes}",
    "{dias_gimnasio}",
    "{dias_libres}",
    "{objetivo}",
    "{split}",
    "{catalogo_ejercicios}",
    "{perfil}",
)


def test_prompt_seed_has_single_default() -> None:
    defaults = [entry for entry in TRAINING_PROMPT_SEED if entry[3]]
    assert len(defaults) == 1
    assert defaults[0][0] == "balanced"


def test_prompt_seed_codes_are_unique() -> None:
    codes = [entry[0] for entry in TRAINING_PROMPT_SEED]
    assert len(codes) == len(set(codes))


def test_prompt_seed_templates_contain_placeholders() -> None:
    for _, _, _, _, system_prompt in TRAINING_PROMPT_SEED:
        assert "{perfil}" in system_prompt
        assert "{objetivo}" in system_prompt
        for placeholder in _PLACEHOLDERS:
            assert placeholder in system_prompt


def test_discipline_mapping_references_existing_prompts() -> None:
    codes = {entry[0] for entry in TRAINING_PROMPT_SEED}
    assert all(prompt_code in codes for _, prompt_code in DISCIPLINE_PROMPT_SEED)


def test_discipline_mapping_references_existing_disciplines() -> None:
    discipline_names = {entry[1] for entry in DISCIPLINE_SEED}
    assert all(name in discipline_names for name, _ in DISCIPLINE_PROMPT_SEED)
