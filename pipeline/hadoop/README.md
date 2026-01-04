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

Run the streaming job with HDFS options:

```bash
docker compose -f pipeline/docker-compose.yml exec spark-master bash -lc '
  spark-submit \
    --master spark://spark-master:7077 \
    --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1 \
    /opt/pipeline/streaming/openstack_streaming_job.py \
      --bootstrap kafka:9092 \
      --raw-topic openstack.raw \
      --features-topic openstack.features \
      --window 60 \
      --slide 30 \
      --hdfs-records-path hdfs://namenode:8020/data/openstack/records \
      --hdfs-features-path hdfs://namenode:8020/data/openstack/features
'
```

Notes:
- `records` is append-only and can be treated as DWD-like detail logs.
- `features` is a snapshot stream (may contain multiple updates per window); downstream can keep the latest by `batch_id`.

