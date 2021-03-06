import subprocess
import time

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, rand
from pyspark.sql.pandas.types import to_arrow_schema

import pyarrow as pa
import pyarrow.flight as pa_flight

from spark_flight_connector import SparkFlightConnector


def main():

    # Location of the Flight Service
    host = '127.0.0.1'
    port = '8888'

    # Unique identifier for flight data
    flight_desc = 'spark-flight-descriptor'

    # --------------------------------------------- #
    # Run Spark to put Arrow data to Flight Service #
    # --------------------------------------------- #
    spark = SparkSession \
        .builder \
        .appName('spark-flight') \
        .getOrCreate()

    start_time = time.time()
    df = spark.read.format("avro").load("file:///Users/vsowrira/git/test_vary_parallel_read_calls-16-8-16-1/")

    # Put the Spark DataFrame to the Flight Service
    SparkFlightConnector.put(df, host, port, flight_desc)

    # ------------------------------------------------------------- #
    # Create a Pandas DataFrame from a pyarrow Flight client reader #
    # ------------------------------------------------------------- #

    # Connect to the Flight service and get endpoints from FlightInfo
    '''
    client = pa_flight.connect((host, int(port)))
    desc = pa_flight.FlightDescriptor.for_path(flight_desc)
    info = client.get_flight_info(desc)
    endpoints = info.endpoints

    # Read all flight endpoints into pyarrow Tables
    tables = []
    for e in endpoints:
        flight_reader = client.do_get(e.ticket)
        table = flight_reader.read_all()
        tables.append(table)

    # Convert Tables to a single Pandas DataFrame
    table = pa.concat_tables(tables)
    pdf = table.to_pandas()
    print("DataFrame from Flight streams:\n %", pdf)
    '''

    # ------------------------------------------------------------- #
    # Create tf.data.Dataset to iterate over Arrow data from Flight #
    # ------------------------------------------------------------- #
    have_tensorflow = False
    try:
        import tensorflow
        import tensorflow_io
        have_tensorflow = True
    except ImportError:
        pass

    if have_tensorflow:
        from tensorflow_flight_dataset import ArrowFlightDataset
        dataset = ArrowFlightDataset.from_schema(host, port, flight_desc, to_arrow_schema(df.schema))
        count = 0
        for row in dataset:
            if count < 10:
                print(row)
                count = count + 1
        dataset.proc.terminate()

    print("Total time taken to read avro data in TF using Spark with Arrow:", (time.time() - start_time))

    spark.stop()


if __name__ == "__main__":
    main()
