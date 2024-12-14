FROM mcr.microsoft.com/playwright:v1.49.0-jammy

# Install Python and X11
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3-pip \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Set Python path for Lambda
ENV PYTHONPATH="/var/task"
ENV LAMBDA_TASK_ROOT="/var/task"

# Install Python packages
COPY requirements.txt .
RUN pip3 install -r requirements.txt \
    awslambdaric

# Copy function code
COPY src/ ${LAMBDA_TASK_ROOT}/src/

# Set the handler
ENTRYPOINT [ "python3", "-m", "awslambdaric" ]
CMD [ "src.lambdas.worker.lambda_handler" ]