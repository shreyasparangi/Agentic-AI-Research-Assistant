# Use the full Python image to avoid compiling C++ libraries from scratch
FROM python:3.10

# Throttle the CPU compiling threads to just 1 core (prevents hardware crashing)
ENV MAX_CONCURRENCY=1
ENV MAKEFLAGS="-j1"

WORKDIR /app

COPY requirements.txt .

# Install without caching, and force pre-compiled binaries where possible
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]