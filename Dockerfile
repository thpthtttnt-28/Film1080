# Use an official Python runtime as a parent image
FROM python:3.10-bullseye

RUN pip install --upgrade pip

RUN apt-get update && \
    apt-get install -y \
        openjdk-11-jdk


ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64/
ENV PATH=$PATH:$JAVA_HOME/bin

# Set the working directory in the container
WORKDIR /app

# Copy all files
COPY . /app/

# Install any needed packages specified in requirements.txt
RUN pip install -r requirements.txt

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define environment variable
ENV NAME intellipurchase

# Run gunicorn when the container launches
CMD ["gunicorn", "-b", "0.0.0.0:8000", "movie_recommender.wsgi:application"]
