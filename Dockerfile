# Use a lightweight Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies (needed for OpenCV/cv2)
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements_dashboard.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
# Note: .dockerignore (if present) or .gitignore logic applies
COPY . .

# Expose port (Cloud Run defaults to 8080)
EXPOSE 8080

# Command to run Streamlit
CMD ["streamlit", "run", "dashboard.py", "--server.port=8080", "--server.address=0.0.0.0"]
