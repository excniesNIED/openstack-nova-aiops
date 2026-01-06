from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import argparse
import hashlib
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql import types as T


DEFAULT_KEYWORDS = [
    "FlavorDiskSmallerThanImage",
    "BuildAbortException",
    "VirtualInterfaceCreateException",
    "Failed to allocate network",
    "qemu unexpectedly closed the monitor",
    "Failed to start libvirt guest",
    "Error launching a defined domain",
]


_REQ_ID_RE = re.compile(r"\breq-[0-9a-f-]{36}\b", re.IGNORECASE)
_INSTANCE_ID_RE = re.compile(r"\binstance:\s*([0-9a-f-]{36})\b", re.IGNORECASE)
_UUID_RE = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE)
_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_MAC_RE = re.compile(r"\b(?:[0-9a-f]{2}:){5}[0-9a-f]{2}\b", re.IGNORECASE)
_ABS_PATH_RE = re.compile(r"/(?:[A-Za-z0-9._-]+/)+[A-Za-z0-9._-]+")
_LONG_NUM_RE = re.compile(r"\b\d{4,}\b")


def _normalize_checkpoint_location(raw: str) -> str:
    """
    Ensure checkpointLocation uses local FS by default.

    With Hadoop configs (fs.defaultFS=hdfs://...), a plain path like "/tmp/..."
    is interpreted as an HDFS path, and may fail due to HDFS root permissions.
    """
    s = (raw or "").strip()
    if not s:
        s = "/tmp/checkpoints/openstack_streaming_job"

    if "://" in s:
        return s

    p = Path(s)
    if not p.is_absolute():
        p = (Path.cwd() / p).absolute()
    return p.as_uri()


def _extract_head_fields(raw_record: str) -> Tuple[str, str, str]:
    """
    Returns (level, component, message) from the head line; continuation is kept elsewhere.
    """
    head = raw_record.splitlines()[0] if raw_record else ""
    stripped = head.strip()
    parts = stripped.split(None, 2)
    if len(parts) == 0:
        return "", "", stripped
    if len(parts) == 1:
        return parts[0], "", ""
    if len(parts) == 2:
        return parts[0], parts[1], ""
    level, component, remainder = parts
    idx = remainder.rfind("] ")
    msg0 = remainder[idx + 2 :] if idx != -1 else remainder

    if "\n" in raw_record:
        # Keep continuation text as part of message for templating/keywords
        rest = "\n".join(raw_record.splitlines()[1:])
        message = msg0 + "\n" + rest
    else:
        message = msg0
    return (level or "").upper(), component, message


def _normalize_message(message: str) -> str:
    normalized = message or ""
    normalized = _UUID_RE.sub("<UUID>", normalized)
    normalized = re.sub(r"\breq-<UUID>\b", "req-<UUID>", normalized, flags=re.IGNORECASE)
    normalized = _IPV4_RE.sub("<IPV4>", normalized)
    normalized = _MAC_RE.sub("<MAC>", normalized)
    normalized = _ABS_PATH_RE.sub("<PATH>", normalized)
    normalized = _LONG_NUM_RE.sub("<NUM>", normalized)
    return normalized


def _template_id(normalized_message: str) -> str:
    return hashlib.sha1((normalized_message or "").encode("utf-8", errors="ignore")).hexdigest()[:8]


def _parse_record_udf(keywords: List[str]):
    def _parse(raw_record: str) -> Dict:
        raw_record = raw_record or ""
        level, component, message = _extract_head_fields(raw_record)

        request_id_match = _REQ_ID_RE.search(raw_record)
        request_id = request_id_match.group(0) if request_id_match else None
        instance_id_match = _INSTANCE_ID_RE.search(raw_record)
        instance_id = instance_id_match.group(1) if instance_id_match else None
        entity_key = instance_id or request_id or "global"

        normalized = _normalize_message(message)
        tpl = _template_id(normalized)

        kw_counts: Dict[str, int] = {}
        for kw in keywords:
            if kw and (kw in message or kw in normalized):
                kw_counts[kw] = kw_counts.get(kw, 0) + 1

        return {
            "level": level,
            "component": component,
            "request_id": request_id,
            "instance_id": instance_id,
            "entity_key": entity_key,
            "message": message,
            "normalized_message": normalized,
            "template_id": tpl,
            "keyword_counts": kw_counts,
        }

    return F.udf(
        _parse,
        T.StructType(
            [
                T.StructField("level", T.StringType(), True),
                T.StructField("component", T.StringType(), True),
                T.StructField("request_id", T.StringType(), True),
                T.StructField("instance_id", T.StringType(), True),
                T.StructField("entity_key", T.StringType(), True),
                T.StructField("message", T.StringType(), True),
                T.StructField("normalized_message", T.StringType(), True),
                T.StructField("template_id", T.StringType(), True),
                T.StructField("keyword_counts", T.MapType(T.StringType(), T.IntegerType()), True),
            ]
        ),
    )


def main() -> None:
    p = argparse.ArgumentParser(description="OpenStack streaming job: openstack.raw -> openstack.features")
    p.add_argument("--bootstrap", default="kafka:9092")
    p.add_argument("--raw-topic", default="openstack.raw")
    p.add_argument("--features-topic", default="openstack.features")
    p.add_argument("--window", type=int, default=60, help="Window size seconds")
    p.add_argument("--slide", type=int, default=30, help="Slide size seconds")
    p.add_argument("--checkpoint", default="/tmp/checkpoints/openstack_streaming_job")
    p.add_argument(
        "--hdfs-records-path",
        default="",
        help="Optional: write parsed records to HDFS as Parquet (e.g. hdfs://namenode:8020/tmp/openstack/records)",
    )
    p.add_argument(
        "--hdfs-features-path",
        default="",
        help="Optional: write window features snapshots to HDFS as Parquet (may contain updates per window)",
    )
    args = p.parse_args()
    checkpoint_base = _normalize_checkpoint_location(args.checkpoint)
    hdfs_records_enabled = bool(args.hdfs_records_path)
    hdfs_features_enabled = bool(args.hdfs_features_path)

    spark = (
        SparkSession.builder.appName("openstack-streaming-job")
        .config("spark.sql.shuffle.partitions", "8")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    raw_schema = T.StructType(
        [
            T.StructField("dataset_id", T.StringType(), True),
            T.StructField("ingest_ts", T.LongType(), True),
            T.StructField("start_line_no", T.IntegerType(), True),
            T.StructField("end_line_no", T.IntegerType(), True),
            T.StructField("raw_record", T.StringType(), True),
        ]
    )

    df_raw = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", args.bootstrap)
        .option("subscribe", args.raw_topic)
        .option("startingOffsets", "latest")
        .load()
    )

    df = df_raw.select(F.col("value").cast("string").alias("value_str"))
    df = df.select(F.from_json(F.col("value_str"), raw_schema).alias("j")).select("j.*")

    # Use ingest_ts (replay time) as event time for windows.
    df = df.withColumn("event_ts", F.to_timestamp(F.from_unixtime(F.col("ingest_ts") / F.lit(1000.0))))

    parse_udf = _parse_record_udf(DEFAULT_KEYWORDS)
    df = df.withColumn("parsed", parse_udf(F.col("raw_record")))

    df_records = df.select(
        "dataset_id",
        "event_ts",
        "start_line_no",
        "end_line_no",
        F.col("raw_record").alias("raw"),
        F.col("parsed.level").alias("level"),
        F.col("parsed.component").alias("component"),
        F.col("parsed.entity_key").alias("entity_key"),
        F.col("parsed.template_id").alias("template_id"),
        F.col("parsed.keyword_counts").alias("keyword_counts"),
    )

    df_records = df_records.withWatermark("event_ts", "5 minutes")
    w = F.window(F.col("event_ts"), f"{args.window} seconds", f"{args.slide} seconds")

    @F.udf(returnType=T.MapType(T.StringType(), T.LongType()))
    def template_counts_udf(template_ids: Optional[List[str]]) -> Dict[str, int]:
        if not template_ids:
            return {}
        counts: Dict[str, int] = {}
        for template_id in template_ids:
            if not template_id:
                continue
            key = str(template_id)
            counts[key] = int(counts.get(key, 0)) + 1
        return counts

    @F.udf(returnType=T.MapType(T.StringType(), T.LongType()))
    def merge_keyword_counts_udf(keyword_maps: Optional[List[Optional[Dict[str, int]]]]) -> Dict[str, int]:
        if not keyword_maps:
            return {}
        merged: Dict[str, int] = {}
        for keyword_map in keyword_maps:
            if not keyword_map:
                continue
            for k, v in keyword_map.items():
                if k is None or v is None:
                    continue
                key = str(k)
                try:
                    merged[key] = int(merged.get(key, 0)) + int(v)
                except Exception:
                    continue
        return merged

    # Best-effort top_templates (take top 10 by count)
    @F.udf(returnType=T.ArrayType(T.StringType()))
    def top_templates_udf(m: Optional[Dict[str, int]]) -> List[str]:
        if not m:
            return []
        items = sorted(m.items(), key=lambda kv: (-int(kv[1]), kv[0]))
        return [k for k, _ in items[:10]]

    df_agg = df_records.groupBy(w.alias("w"), "entity_key").agg(
        F.first("dataset_id").alias("dataset_id"),
        F.count(F.lit(1)).alias("total_records"),
        F.sum(F.when(F.col("level") == F.lit("ERROR"), F.lit(1)).otherwise(F.lit(0))).alias("error_cnt"),
        F.sum(
            F.when((F.col("level") == F.lit("WARNING")) | (F.col("level") == F.lit("WARN")), F.lit(1)).otherwise(F.lit(0))
        ).alias("warn_cnt"),
        F.sum(F.when(F.col("level") == F.lit("INFO"), F.lit(1)).otherwise(F.lit(0))).alias("info_cnt"),
        F.collect_list("template_id").alias("template_ids"),
        F.collect_list("keyword_counts").alias("keyword_maps"),
        F.collect_list(
            F.when(
                F.col("level") == F.lit("ERROR"),
                F.struct(
                    F.col("start_line_no").alias("start_line_no"),
                    F.col("end_line_no").alias("end_line_no"),
                    F.col("component").alias("component"),
                    F.col("raw").alias("raw"),
                ),
            )
        ).alias("error_examples_raw"),
    )

    df_agg = df_agg.withColumn("template_counts", template_counts_udf(F.col("template_ids"))).drop("template_ids")
    df_agg = df_agg.withColumn("keyword_counts", merge_keyword_counts_udf(F.col("keyword_maps"))).drop("keyword_maps")
    df_agg = df_agg.withColumn(
        "error_examples",
        F.expr("slice(filter(error_examples_raw, x -> x is not null), 1, 5)"),
    ).drop("error_examples_raw")

    df_agg = df_agg.withColumn(
        "error_ratio",
        F.when(F.col("total_records") > 0, F.col("error_cnt") / F.col("total_records")).otherwise(F.lit(0.0)),
    )
    df_agg = df_agg.withColumn("window_start", F.col("w.start"))
    df_agg = df_agg.withColumn("window_end", F.col("w.end"))
    df_agg = df_agg.withColumn("top_templates", top_templates_udf(F.col("template_counts")))

    df_features = df_agg.select(
        F.col("entity_key"),
        F.coalesce(F.col("dataset_id"), F.lit("")).alias("dataset_id"),
        F.col("window_start").alias("window_start"),
        F.col("window_end").alias("window_end"),
        F.col("template_counts"),
        F.coalesce(F.col("keyword_counts"), F.create_map()).alias("keyword_counts"),
        F.coalesce(F.col("error_examples"), F.array()).alias("error_examples"),
        F.coalesce(F.col("top_templates"), F.array()).alias("top_templates"),
        F.coalesce(F.col("error_cnt"), F.lit(0)).alias("error_cnt"),
        F.coalesce(F.col("warn_cnt"), F.lit(0)).alias("warn_cnt"),
        F.coalesce(F.col("info_cnt"), F.lit(0)).alias("info_cnt"),
        F.coalesce(F.col("total_records"), F.lit(0)).alias("total_records"),
        F.coalesce(F.col("error_ratio"), F.lit(0.0)).alias("error_ratio"),
    )

    def _write_features_batch(batch_df, batch_id: int) -> None:
        nonlocal hdfs_features_enabled
        kafka_df = batch_df.select(
            F.col("entity_key").cast("string").alias("key"),
            F.to_json(
                F.struct(
                    F.col("entity_key"),
                    F.col("dataset_id"),
                    F.col("window_start").cast("string").alias("window_start"),
                    F.col("window_end").cast("string").alias("window_end"),
                    F.col("template_counts"),
                    F.col("keyword_counts"),
                    F.col("error_examples"),
                    F.col("top_templates"),
                    F.col("error_cnt"),
                    F.col("warn_cnt"),
                    F.col("info_cnt"),
                    F.col("total_records"),
                    F.col("error_ratio"),
                )
            ).alias("value"),
        )
        (
            kafka_df.write.format("kafka")
            .option("kafka.bootstrap.servers", args.bootstrap)
            .option("topic", args.features_topic)
            .save()
        )

        if args.hdfs_features_path and hdfs_features_enabled:
            try:
                (
                    batch_df.withColumn("batch_id", F.lit(int(batch_id)))
                    .withColumn("dt", F.date_format(F.col("window_start"), "yyyy-MM-dd"))
                    .write.mode("append")
                    .partitionBy("dt", "dataset_id")
                    .parquet(args.hdfs_features_path)
                )
            except Exception as e:
                hdfs_features_enabled = False
                print(
                    f"WARNING: failed to write features Parquet to '{args.hdfs_features_path}'; disabling HDFS features sink. {e}",
                    file=sys.stderr,
                )

    def _write_records_batch(batch_df, batch_id: int) -> None:
        nonlocal hdfs_records_enabled
        if not (args.hdfs_records_path and hdfs_records_enabled):
            return
        try:
            (
                batch_df.withColumn("batch_id", F.lit(int(batch_id)))
                .withColumn("dt", F.date_format(F.col("event_ts"), "yyyy-MM-dd"))
                .write.mode("append")
                .partitionBy("dt", "dataset_id")
                .parquet(args.hdfs_records_path)
            )
        except Exception as e:
            hdfs_records_enabled = False
            print(
                f"WARNING: failed to write records Parquet to '{args.hdfs_records_path}'; disabling HDFS records sink. {e}",
                file=sys.stderr,
            )

    _ = (
        df_features.writeStream.outputMode("update")
        .foreachBatch(_write_features_batch)
        .option("checkpointLocation", checkpoint_base)
        .start()
    )

    if args.hdfs_records_path:
        records_checkpoint = f"{checkpoint_base.rstrip('/')}/records"
        _ = (
            df_records.writeStream.outputMode("append")
            .foreachBatch(_write_records_batch)
            .option("checkpointLocation", records_checkpoint)
            .start()
        )

    spark.streams.awaitAnyTermination()


if __name__ == "__main__":
    main()
