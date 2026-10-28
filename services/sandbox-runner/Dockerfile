# Exact Python release; runtime resolves the built image to an immutable image ID.
FROM python:3.12.14-slim-bookworm
RUN python -m pip install --no-cache-dir pytest==8.3.5
ENV PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 HOME=/tmp
USER 65532:65532
WORKDIR /workspace
ENTRYPOINT ["python", "-m", "pytest"]
