from ...schemas import ModerationResult
from .provider import generate


def moderate(text):
    def fallback():
        flagged = any(
            word in text.lower()
            for word in [
                "free money",
                "password",
                "пароль",
                "взлом",
                "malware",
                "spam",
                "казино",
                "оскорб",
            ]
        )
        return ModerationResult(
            status="REVIEW_REQUIRED" if flagged else "CLEAN",
            reasons=(
                [
                    "Есть потенциально нежелательное содержание; требуется решение администратора."
                ]
                if flagged
                else []
            ),
        )

    return generate(
        ModerationResult,
        "Flag potential spam, offensive, unrelated, fake or malicious content for human review. Never delete or hide automatically.",
        {"text": text[:20000]},
        fallback,
    )
