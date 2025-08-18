# Use official Python image as base
FROM python:3.13-alpine

RUN apk add --no-cache git

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
# Copy the rest of the application code
ARG GIT_REPO=https://github.com/KasaCompaniesIT/pyKasaWireLabel.git
RUN git clone ${GIT_REPO} . || (echo "Failed to clone repository" && exit 1)

RUN pip install --no-cache-dir -r requirements-minimal.txt

# Expose Flask port
EXPOSE 5000

# Run the Flask app
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
