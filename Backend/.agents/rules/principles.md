---
description: "Non-negotiable principles for Fasal Twin backend"
globs: ["**/*"]
---

# Non-negotiable Principles (Fasal Twin)

1. **Never fabricate a number.**
   - If a required data file is missing, empty, or doesn't match the expected schema, stop that step, print a clear message naming exactly which file/column is missing, and continue building the rest of the pipeline around a clearly-marked stub.
   - Do not interpolate, guess, or silently substitute a plausible-looking value.

2. **Every model output must carry a confidence label and a data-provenance note.**
   - Example: "based on 12 years of Agmarknet history" vs. "based on 3 years — low confidence".
   - Confidence is derived strictly from actual data density, never hardcoded as a fixed percentage.

3. **No IoT hardware, no live satellite dependency.**
   - Any "crop maturity" input is either read from a CSV the user supplies or explicitly treated as unavailable.
   - Never use a hardcoded live-feed simulation dressed up as real data.

4. **The system must be able to say "I don't have enough data to recommend an action here".**
   - This is a feature, not a failure mode.
   - Build this as an explicit code path, not an afterthought.
