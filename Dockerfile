FROM public.ecr.aws/lambda/python:3.11

# Install playwright dependencies
RUN yum install -y \
    atk \
    cups-libs \
    gtk3 \
    libXcomposite \
    libXcursor \
    libXdamage \
    libXext \
    libXi \
    libXrandr \
    libXScrnSaver \
    libXtst \
    pango \
    xorg-x11-server-Xvfb \
    alsa-lib

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN playwright install chromium
RUN playwright install-deps

# Copy function code
COPY src/ ${LAMBDA_TASK_ROOT}/src/

# Use environment variable to determine which handler to use
CMD [ "${HANDLER:-src.lambda.worker.lambda_handler}" ]