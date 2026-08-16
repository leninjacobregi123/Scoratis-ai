"""
Retry behaviour for transient provider failures.

Sofie enforces per-key rate and daily-token limits, and a lesson fans out
into many model calls, so a 429 mid-batch used to lose the whole lesson.
These assertions pin the parts that are easy to get subtly wrong: what is
retried, what is not, and how long we are prepared to wait.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from services.litellm_service import (  # noqa: E402
    RETRYABLE_ERROR_TYPES, MAX_RETRY_ATTEMPTS, MAX_RETRY_DELAY,
    BASE_RETRY_DELAY, _retry_delay,
)

failures = []


def check(label, condition, detail=""):
    if condition:
        print(f"pass  {label}")
    else:
        failures.append(label)
        print(f"FAIL  {label} {detail}")


# --- the retryable set must describe reality ---------------------------
source = (Path(__file__).resolve().parents[2] / "services" / "litellm_service.py").read_text()
produced = set(re.findall(r'error_type="([a-z_]+)"', source))

check("every retryable name is one the code actually produces",
      not (RETRYABLE_ERROR_TYPES - produced),
      str(sorted(RETRYABLE_ERROR_TYPES - produced)))

# Waiting cannot fix a bad key or a model that does not exist, and retrying
# only delays telling the user.
for never in ("authentication_error", "model_not_found"):
    check(f"{never} is never retried", never not in RETRYABLE_ERROR_TYPES)

for always in ("rate_limit", "timeout", "service_unavailable"):
    check(f"{always} is retried", always in RETRYABLE_ERROR_TYPES)


# --- backoff shape ------------------------------------------------------
class _WithRetryAfter:
    retry_after = 7


class _AbsurdRetryAfter:
    retry_after = 99999


class _JunkRetryAfter:
    retry_after = "soon"


delays = [_retry_delay(i) for i in range(MAX_RETRY_ATTEMPTS)]
check("every delay is positive", all(d > 0 for d in delays), str(delays))
check("no delay exceeds the cap", all(d <= MAX_RETRY_DELAY for d in delays), str(delays))

# Jitter means successive attempts are not strictly ordered, but the ceiling
# must still grow - otherwise this is a fixed delay wearing a costume.
check("backoff grows across attempts",
      max(_retry_delay(0) for _ in range(50)) < max(_retry_delay(3) for _ in range(50)))

sample = {round(_retry_delay(1), 6) for _ in range(40)}
check("delays are jittered, not identical", len(sample) > 1, f"{len(sample)} distinct")

check("Retry-After is honoured", abs(_retry_delay(0, _WithRetryAfter()) - 7) < 0.01)
check("an absurd Retry-After is capped",
      _retry_delay(0, _AbsurdRetryAfter()) <= MAX_RETRY_DELAY)
check("junk Retry-After falls back to backoff",
      0 < _retry_delay(0, _JunkRetryAfter()) <= MAX_RETRY_DELAY)

# --- the total wait has to stay bounded ---------------------------------
worst_case = sum(min(BASE_RETRY_DELAY * (2 ** i), MAX_RETRY_DELAY)
                 for i in range(MAX_RETRY_ATTEMPTS - 1))
check("worst-case total wait stays under a minute", worst_case < 60,
      f"{worst_case:.0f}s")
check("more than one attempt is actually made", MAX_RETRY_ATTEMPTS >= 2)


def test_no_failures():
    """Pytest entry point. The checks above run at import; this asserts them."""
    assert not failures, "; ".join(failures)


if __name__ == "__main__":
    print("\nALL PASS" if not failures else f"\n{len(failures)} FAILED: {failures}")
    sys.exit(0 if not failures else 1)
