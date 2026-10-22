# Optional AI workspace (deferred)

The AI Board Assistant page is intentionally excluded from the manual-first local
desktop experience. The deterministic planner and engineering checks remain the
runtime path for this milestone.

The assistant implementation module remains in `src/ai_planner_assistant.py`,
and the original Streamlit page can be recovered from the repository's Git
history if/when the optional AI phase resumes. The existing development
`requirements.txt` retains its OpenAI dependency; local users install only
`requirements-local.txt`.
