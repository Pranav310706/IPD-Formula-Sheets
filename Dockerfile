FROM python:3.11-slim

# System deps needed by pillow/matplotlib
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libsm6 libxrender1 libxext6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /formula_sheet_refined

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cloud hosts (Render/Railway/etc.) inject $PORT at runtime; default to 5050 locally
ENV PORT=5050
EXPOSE 5050

# --timeout raised because the pix2tex model can take a few seconds to warm up
CMD gunicorn -w 1 -k gthread --threads 4 --timeout 120 -b 0.0.0.0:$PORT formula_sheet_refined:app
