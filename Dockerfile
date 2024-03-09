# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies required for uWSGI compilation
RUN apt-get update && apt-get install -y \
    gcc \
    libc6-dev \
    libpcre3-dev \
    && rm -rf /var/lib/apt/lists/*


# Set work directory
WORKDIR /usr/src/app

# Install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Install uwsgi
RUN pip install uwsgi

# Copy project
COPY . .

# uwsgi.ini configuration
COPY uwsgi.ini /usr/src/app/uwsgi.ini

# Expose port 8000 for uwsgi
EXPOSE 8000

# Run uwsgi
CMD ["uwsgi", "--ini", "uwsgi.ini"]
