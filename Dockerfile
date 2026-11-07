FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .
# Simplest option: results/ (and optional disclosures.json) are copied in and the site is
# built at image build time, so a new result means a redeploy. No runtime state.
COPY results ./results
COPY disclosures.json ./
RUN guardrailbench leaderboard --results results --out site --disclosures disclosures.json
# Railway sets PORT.
CMD ["sh", "-c", "python -m http.server $PORT --directory site"]
