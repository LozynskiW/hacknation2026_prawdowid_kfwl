"""Wspólna baza dla kontraktów między modułami."""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

SCHEMA_VERSION = "1.0"


class ContractModel(BaseModel):
    """Bazowy model kontraktu.

    - pola w Pythonie w snake_case, w JSON w camelCase,
    - niezmienny (frozen) - moduł nie modyfikuje danych poprzednika,
    - nieznane pola są błędem (extra="forbid").
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    def to_json(self) -> str:
        """Serializacja do JSON w formacie kontraktu (camelCase)."""
        return self.model_dump_json(by_alias=True, exclude_none=True)
