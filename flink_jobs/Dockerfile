# PyFlink needs a JVM. Bullseye ships openjdk-11 (Flink 1.18's primary JDK);
# bookworm dropped JDK 11, so we pin the bullseye variant on purpose.
# Python 3.10: apache-flink 1.18.1 publishes wheels only up to cp310 — on 3.11
# pip falls back to the sdist, whose build deps pin numpy==1.21.4 (no 3.11 build).
FROM python:3.10-slim-bullseye

WORKDIR /app

# Java 11 runtime + build tools for the native wheels PyFlink/duckdb pull in
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential curl openjdk-11-jre-headless \
    && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
ENV PATH="${JAVA_HOME}/bin:${PATH}"

# Flink DataStream Kafka connector fat-JAR (matches apache-flink 1.18.x).
# The job discovers it in FLINK_JARS_DIR and registers it via env.add_jars(...).
ENV FLINK_JARS_DIR=/opt/flink-jars
RUN mkdir -p ${FLINK_JARS_DIR} && \
    curl -fsSL -o ${FLINK_JARS_DIR}/flink-sql-connector-kafka-3.1.0-1.18.jar \
      https://repo1.maven.org/maven2/org/apache/flink/flink-sql-connector-kafka/3.1.0-1.18/flink-sql-connector-kafka-3.1.0-1.18.jar

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "feature_job.py"]
