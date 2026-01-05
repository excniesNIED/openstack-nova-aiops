# Hadoop (HDFS) Persistence — Optional

This project can optionally persist streaming outputs to HDFS (Parquet) to match the “big data storage” expectation.

## Start HDFS

```bash
docker compose -f pipeline/docker-compose.yml --profile hadoop up -d
```

- NameNode UI: `http://localhost:9870`
- DataNode UI: `http://localhost:9864`

`hdfs-init` will create:

- `/data/openstack/records`
- `/data/openstack/features`

## Write Parquet from Spark Streaming

By default, `pipeline/docker-compose.yml` runs the streaming job in `spark-streaming`.

When HDFS is enabled (`--profile hadoop`), `spark-streaming` will auto-detect `namenode:8020` and enable Parquet sinks.

To observe the job:

```bash
docker compose -f pipeline/docker-compose.yml ps spark-streaming
docker compose -f pipeline/docker-compose.yml logs -f spark-streaming
```

If you need to run it manually with explicit HDFS options:

```bash
docker compose -f pipeline/docker-compose.yml exec spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.3,org.apache.spark:spark-token-provider-kafka-0-10_2.12:3.5.3 /opt/pipeline/streaming/openstack_streaming_job.py --bootstrap kafka:9092 --raw-topic openstack.raw --features-topic openstack.features --window 60 --slide 30 --checkpoint /opt/checkpoints/openstack_streaming_job --hdfs-records-path hdfs://namenode:8020/data/openstack/records --hdfs-features-path hdfs://namenode:8020/data/openstack/features
```

Notes:
- `records` is append-only and can be treated as DWD-like detail logs.
- `features` is a snapshot stream (may contain multiple updates per window); downstream can keep the latest by `batch_id`.
