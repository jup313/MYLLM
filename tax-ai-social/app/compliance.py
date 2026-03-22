"""
Tax Industry Compliance Filter
Blocks content that could violate IRS regulations, FTC rules,
or create legal liability for a tax services firm.
"""

# Phrases that are legally risky or misleading for tax services
FORBIDDEN_PHRASES = [
    "guaranteed refund",
    "guarantee a refund",
    "guaranteed tax refund",
    "eliminate all tax debt",
    "eliminate your tax debt",
    "wipe out your taxes",
    "irs can't touch you",
    "irs won't come after you",
    "legal tax loophole",
    "secret tax loophole",
    "pay zero taxes",
    "never pay taxes again",
    "avoid paying taxes",
    "100% tax free",
    "offshore account",
    "hide money",
    "hide income",
    "under the table",
    "don't report",
    "not report income",
    "beat the irs",
    "cheat the irs",
    "tax shelter scheme",
    "100% deductible",
    "write off everything",
    "deduct anything",
    "guaranteed settlement",
    "pennies on the dollar guaranteed",
    "make the irs disappear",
    "stop irs immediately",
    "get rid of irs",
    "eliminate irs debt overnight",
    "tax free forever",
    "no taxes owed",
    "debt forgiven instantly",
    "reduce tax by 90%",
    "reduce taxes by 80%",
]

# Phrases that should trigger a compliance warning (not block, but flag)
WARNING_PHRASES = [
    "settle for less",
    "reduce your tax debt",
    "irs settlement",
    "offer in compromise",
    "pennies on the dollar",
    "tax relief",
    "audit protection",
    "audit proof",
    "maximize deductions",
    "get a bigger refund",
    "bigger tax refund",
]

# Required disclaimer triggers — if these topics appear, suggest a disclaimer
DISCLAIMER_TRIGGERS = [
    "tax advice",
    "tax strategy",
    "deduction",
    "write off",
    "tax credit",
    "irs",
    "audit",
    "tax return",
    "tax planning",
]

DISCLAIMER_TEXT = "⚠️ This is for educational purposes only. Consult a licensed tax professional for advice specific to your situation."


def compliance_check(text):
    """
    Returns a dict:
    {
        "passed": bool,
        "blocked_phrases": list,
        "warning_phrases": list,
        "disclaimer_suggested": bool,
        "score": int (0-100, higher = more compliant)
    }
    """
    text_lower = text.lower()
    
    blocked = [p for p in FORBIDDEN_PHRASES if p in text_lower]
    warnings = [p for p in WARNING_PHRASES if p in text_lower]
    needs_disclaimer = any(t in text_lower for t in DISCLAIMER_TRIGGERS)
    
    passed = len(blocked) == 0
    
    # Score: start at 100, deduct for issues
    score = 100
    score -= len(blocked) * 25
    score -= len(warnings) * 5
    score = max(0, score)
    
    return {
        "passed": passed,
        "blocked_phrases": blocked,
        "warning_phrases": warnings,
        "disclaimer_suggested": needs_disclaimer,
        "score": score
    }


def add_disclaimer_if_needed(text, result):
    """Append disclaimer to post if triggered."""
    if result.get("disclaimer_suggested") and DISCLAIMER_TEXT not in text:
        return text + f"\n\n{DISCLAIMER_TEXT}"
    return text


def get_compliance_summary(result):
    """Return a human-readable compliance summary string."""
    if result["passed"]:
        summary = f"✅ Compliance PASSED (score: {result['score']}/100)"
        if result["warning_phrases"]:
            summary += f"\n⚠️  Warnings: {', '.join(result['warning_phrases'])}"
        if result["disclaimer_suggested"]:
            summary += "\nℹ️  Disclaimer suggested"
    else:
        summary = f"❌ Compliance FAILED (score: {result['score']}/100)"
        summary += f"\n🚫 Blocked phrases: {', '.join(result['blocked_phrases'])}"
    return summary
