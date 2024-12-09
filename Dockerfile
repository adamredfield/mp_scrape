FROM public.ecr.aws/lambda/python:3.13

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy function code
COPY src/ ${LAMBDA_TASK_ROOT}/src/

# Set the CMD to your handler
CMD [ "src.lambda.orchestrator.lambda_handler" ]