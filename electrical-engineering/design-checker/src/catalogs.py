"""Shared discrete engineering choice catalogs.

Keep UI-selectable rating series in one backend-owned location so calculators,
future board-planning workflows, and tests do not duplicate conventional values.
These catalogs are declared tool scope, not a claim that every rating is suitable
for every product, manufacturer, or standards context.
"""

# Conventional breaker candidates currently used by the automatic circuit selector.
BREAKER_RATINGS_A = (
    6,
    10,
    16,
    20,
    25,
    32,
    40,
    50,
    63,
    80,
    100,
    125,
    160,
    200,
    250,
    315,
    400,
    500,
    630,
)
