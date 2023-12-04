# Use the official Python image from the Docker Hub
FROM python:3

# Set the working directory inside the container
ADD main.py .

# Copy the current directory contents into the container at /app
COPY . /fastapi
WORKDIR /fastapi
COPY ./requirements.txt /fastapi/requirements.txt
# Install any necessary dependencies
RUN pip install --no-cache-dir --upgrade -r /fastapi/requirements.txt

# Command to run the FastAPI server when the container starts
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]