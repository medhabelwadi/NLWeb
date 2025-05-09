FROM mcr.microsoft.com/devcontainers/python:1.2.2-3.13-bookworm

# Add python items which are not in our requirements.txt
RUN pip3 --no-cache-dir install go-task-bin

# Run the python requirements
COPY ./code/requirements.txt /tmp/pip-tmp/
RUN pip3 --disable-pip-version-check --no-cache-dir install -r /tmp/pip-tmp/requirements.txt \
   && rm -rf /tmp/pip-tmp

# Copy in our code
WORKDIR /

# Add the src directory
ADD ./code code
ADD ./static static

# Add other selected files from base repo directory
ADD ./code/requirements.txt code/requirements.txt
   
# Set the PYTHONPATH environment variable
ENV PYTHONPATH=/code

# Expose port for SocketIO connection to the server
EXPOSE 8000

ENTRYPOINT [ "python", "/code/webserver/WebServer.py"]

