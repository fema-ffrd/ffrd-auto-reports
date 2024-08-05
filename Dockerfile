FROM python:3.10-slim

# Install libgdal-dev
USER root
RUN apt-get update && apt-get install -y \
    libgdal-dev \
    libsqlite3-dev \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

# Clean up
RUN apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Clone the repo
RUN git clone https://github.com/fema-ffrd/ffrd-auto-reports.git .

RUN pip3 install -r requirements.txt

EXPOSE 8501

# run the streamlit app
CMD ["streamlit", "run", "src/Auto-Report.py"]