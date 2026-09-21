FROM python:3.11-slim

# --------------------------------------------------
# System dependencies
# --------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# --------------------------------------------------
# Working directory
# --------------------------------------------------
WORKDIR /formula_sheet_refined

# --------------------------------------------------
# Python dependencies
# --------------------------------------------------
COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# --------------------------------------------------
# Application files
# --------------------------------------------------
COPY . .

ENV NO_ALBUMENTATIONS_UPDATE=1

# --------------------------------------------------
# Cloud platforms provide PORT at runtime
# --------------------------------------------------
ENV PORT=5050

EXPOSE 5050

# --------------------------------------------------
# Start Flask through Gunicorn
# --------------------------------------------------
CMD ["sh", "-c", "gunicorn --workers 1 --worker-class gthread --threads 4 --timeout 180 --bind 0.0.0.0:${PORT} formula_sheet_refined:app"]
