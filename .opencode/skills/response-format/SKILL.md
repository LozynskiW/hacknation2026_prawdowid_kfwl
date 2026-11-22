---
name: response-format
description: Użyj, żeby sformatować raport odnośnie weryfikacji twierdzeń na stronach
version: 1.0.0
tags: [fact-checking, verdict-formulation, plain-language, attribution, refusal-handling]
---

# FORMAT ODPOWIEDZI (obowiązkowy)

Odpowiedz WYŁĄCZNIE jednym obiektem JSON, bez żadnego tekstu przed ani po:

```json
{
  "original_message": "wiadomość użytkownika bez zmian",
  "overall_verdict": {
    "potwierdzone": 0,
    "falszywe": 0,
    "wprowadzajace_w_blad": 0,
    "brak_wystarczajacych_dowodow": 0,
    "nie_podlega_weryfikacji": 0
  },
  "confidence_score": "POTWIERDZONE | FALSZYWE | WPROWADZAJACE_W_BLAD | BRAK_WYSTARCZAJACYCH_DOWODOW | NIE_PODLEGA_WERYFIKACJI",
  "executive_summary": "2-4 proste zdania po polsku: co sprawdzono i jaki jest wynik",
  "claims": [
    {
      "claim_id": "TWIERDZENIE-001",
      "evaluated_claim": "twierdzenie w jednym zdaniu",
      "verdict": "POTWIERDZONE | FALSZYWE | WPROWADZAJACE_W_BLAD | BRAK_WYSTARCZAJACYCH_DOWODOW | NIE_PODLEGA_WERYFIKACJI",
      "confidence_score": 0.0,
      "summary_response_pl": "krótka odpowiedź w jednym zdaniu",
      "detailed_justification_pl": "uzasadnienie oparte na źródłach, 2-5 zdań",
      "refusal_to_judge": {"is_refused": false, "reason": null},
      "sources_used": [
        {"title": "tytuł", "publisher": "wydawca", "publication_date": "RRRR-MM-DD",
         "url": "https://...", "exact_quote": "dosłowny fragment"}
      ]
    }
  ],
  "error": null
}
```

Zasady:
- `confidence_score` w twierdzeniu: liczba od 0 do 1.
- `NIE_PODLEGA_WERYFIKACJI` dla opinii i prognoz. `BRAK_WYSTARCZAJACYCH_DOWODOW`, gdy nie ma pewnego źródła.
- `refusal_to_judge.is_refused: true` i powód, gdy odmawiasz oceny.
- Pusta lista `claims`, gdy w wiadomości nie ma nic do sprawdzenia - wtedy w `executive_summary` napisz, co użytkownik ma doprecyzować.
- `error` tylko przy błędzie technicznym (tekst), w pozostałych przypadkach `null`.
- Podawaj tylko źródła, które naprawdę istnieją. Nie wymyślaj adresów, dat ani cytatów.
- Maks. 5 twierdzeń.
