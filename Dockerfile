FROM mcr.microsoft.com/playwright:v1.49.0-jammy

# Install Python and pip
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3-pip \
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

# Install AWS Lambda Runtime Interface Client
RUN pip3 install awslambdaric

# Set the handler
ENTRYPOINT [ "/usr/local/bin/python3", "-m", "awslambdaric" ]
CMD [ "src.lambda.worker.lambda_handler" ]