FROM public.ecr.aws/amazonlinux/amazonlinux:2023

# Install Python 3.11 and system dependencies
RUN dnf install -y python3.11 pip \
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
    nodejs \
    npm

# Set Python path
ENV PYTHONPATH="/var/task"
ENV LAMBDA_TASK_ROOT="/var/task"

# Install specific version of Playwright
COPY requirements.txt .
RUN pip3.11 install -r requirements.txt
RUN pip3.11 install playwright==1.30.0

# Install browser
ENV PLAYWRIGHT_BROWSERS_PATH=/tmp/playwright-browsers
RUN python3.11 -m playwright install-deps
RUN PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 python3.11 -m playwright install chromium

# Copy function code
COPY src/ ${LAMBDA_TASK_ROOT}/src/

# Set the handler
CMD [ "python3.11", "-m", "awslambdaric", "src.lambda.worker.lambda_handler" ]