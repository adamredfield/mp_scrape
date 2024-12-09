FROM public.ecr.aws/lambda/python:3.11

# Install system dependencies and newer glibc
RUN yum update -y && \
    yum install -y \
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
    alsa-lib \
    glibc \
    glibc-devel

# Install Python packages
COPY requirements.txt .
RUN pip install -r requirements.txt

# Install browser with specific version that works with this environment
ENV PLAYWRIGHT_BROWSERS_PATH=/tmp/playwright-browsers
RUN playwright install --with-deps chromium

# Copy function code
COPY src/ ${LAMBDA_TASK_ROOT}/src

# Default to worker handler
CMD [ "src.lambda.worker.lambda_handler" ]