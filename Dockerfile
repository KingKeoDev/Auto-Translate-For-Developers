# 1. Base image
FROM python:3.13-slim

# 2. Work directory
WORKDIR /app

# 3. Dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 4. App code
COPY . .


# 6. Expose port
EXPOSE 5000

# 7. Run the app
CMD ["python", "src/main.py"]