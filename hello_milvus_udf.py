# hello_milvus_udf.py demonstrates the basic operations of PyMilvus, a Python SDK of Milvus.
# 1. connect to Milvus
# 2. create collection
# 3. insert data
# 4. create index
# 5. search, query, and hybrid search on entities
# 6. delete entities by PK
# 7. drop collection
import time

import numpy as np
import base64
from pymilvus import (
    connections,
    utility,
    FieldSchema, CollectionSchema, DataType,
    Collection,
)

fmt = "\n=== {:30} ===\n"
search_latency_fmt = "search latency = {:.4f}s"
num_entities, dim = 30, 8

#################################################################################
# 1. connect to Milvus
# Add a new connection alias `default` for Milvus server in `localhost:19530`
# Actually the "default" alias is a buildin in PyMilvus.
# If the address of Milvus is the same as `localhost:19530`, you can omit all
# parameters and call the method as: `connections.connect()`.
#
# Note: the `using` parameter of the following methods is default to "default".
print(fmt.format("start connecting to Milvus"))
connections.connect("default", host="localhost", port="19530")
has = utility.has_collection("hello_milvus_udf")
print(f"Does collection hello_milvus_udf exist in Milvus: {has}")

if has:
    utility.drop_collection("hello_milvus_udf")
    has = utility.has_collection("hello_milvus_udf")
    print(f"Does collection hello_milvus_udf exist in Milvus: {has}")

#################################################################################
# 2. create collection
# We're going to create a collection with 7 fields.
# +-+------------+------------+------------------+------------------------------+
# | | field name | field type | other attributes |       field description      |
# +-+------------+------------+------------------+------------------------------+
# |1|    "pk"    |   VarChar  |  is_primary=True |      "primary field"         |
# | |            |            |   auto_id=False  |                              |
# +-+------------+------------+------------------+------------------------------+
# |2|  "random"  |    Double  |                  |      "a double field"        |
# +-+------------+------------+------------------+------------------------------+
# |3|  "age8"    |    Int8    |                  |      "a int8 field"          |
# +-+------------+------------+------------------+------------------------------+
# |4|  "age16"   |    Int16   |                  |      "a int16 field"         |
# +-+------------+------------+------------------+------------------------------+
# |5|  "age32"   |    Int32   |                  |      "a int32 field"         |
# +-+------------+------------+------------------+------------------------------+
# |6|  "age64"   |    Int64   |                  |      "a int64 field"         |
# +-+------------+------------+------------------+------------------------------+
# |7|"embeddings"| FloatVector|     dim=8        |  "float vector with dim 8"   |
# +-+------------+------------+------------------+------------------------------+
fields = [
    FieldSchema(name="pk", dtype=DataType.VARCHAR,
                is_primary=True, auto_id=False, max_length=100),
    FieldSchema(name="random", dtype=DataType.DOUBLE),
    FieldSchema(name="age8", dtype=DataType.INT8),
    FieldSchema(name="age16", dtype=DataType.INT16),
    FieldSchema(name="age32", dtype=DataType.INT32),
    FieldSchema(name="age64", dtype=DataType.INT64),
    FieldSchema(name="embeddings", dtype=DataType.FLOAT_VECTOR, dim=dim)
]

schema = CollectionSchema(
    fields, "hello_milvus_udf is the simplest demo to introduce the APIs")

print(fmt.format("Create collection `hello_milvus_udf`"))
hello_milvus_udf = Collection(
    "hello_milvus_udf", schema, consistency_level="Strong")

################################################################################
# 3. insert data
# We are going to insert 3000 rows of data into `hello_milvus_udf`
# Data to be inserted must be organized in fields.
#
# The insert() method returns:
# - either automatically generated primary keys by Milvus if auto_id=True in the schema;
# - or the existing primary key field from the entities if auto_id=False in the schema.

print(fmt.format("Start inserting entities"))
rng = np.random.default_rng(seed=19530)
entities = [
    # provide the pk field because `auto_id` is set to False
    [str(i) for i in range(num_entities)],
    rng.random(num_entities).tolist(),  # field random, only supports list
    rng.integers(100, size=num_entities, dtype=np.int8),
    rng.integers(2000, size=num_entities, dtype=np.int16),
    rng.integers(2000, size=num_entities, dtype=np.int32),
    rng.integers(2000, size=num_entities, dtype=np.int64),
    # [np.random.randint(1, 10000) for _ in range(num_entities)],
    # field embeddings, supports numpy.ndarray and list
    rng.random((num_entities, dim)),
]

insert_result = hello_milvus_udf.insert(entities)
################################################################################
# 4. create index
# We are going to create an IVF_FLAT index for hello_milvus_udf collection.
# create_index() can only be applied to `FloatVector` and `BinaryVector` fields.
print(fmt.format("Start Creating index IVF_FLAT"))
index = {
    "index_type": "IVF_FLAT",
    "metric_type": "L2",
    "params": {"nlist": 128},
}

hello_milvus_udf.create_index("embeddings", index)

################################################################################
# 4. create function
# We are going to create some udf funciton for hello_milvus_udf collection.

wat_body = """(module
  (type (;0;) (func (param i64 i64) (result i32)))
  (func $greater_than (type 0) (param i64 i64) (result i32)
    local.get 0
    local.get 1
    i64.gt_s)
  (table (;0;) 1 1 funcref)
  (memory (;0;) 16)
  (global $__stack_pointer (mut i32) (i32.const 1048576))
  (global (;1;) i32 (i32.const 1048576))
  (global (;2;) i32 (i32.const 1048576))
  (export "memory" (memory 0))
  (export "greater_than" (func $greater_than))
  (export "__data_end" (global 1))
  (export "__heap_base" (global 2)))"""
wat_body_base64 = base64.b64encode(wat_body.encode('UTF-8'))
arg_types = [DataType.INT64, DataType.INT64]
utility.create_function("greater_than", wat_body_base64, arg_types)

wat_body_base64 = "KG1vZHVsZQogICh0eXBlICg7MDspIChmdW5jIChwYXJhbSBpMzIgaTMyIGkzMiBpNjQgaTY0KSAocmVzdWx0IGkzMikpKQogIChmdW5jICRtdWx0aXBsZV9jb2x1bW5zICh0eXBlIDApIChwYXJhbSBpMzIgaTMyIGkzMiBpNjQgaTY0KSAocmVzdWx0IGkzMikKICAgIGxvY2FsLmdldCAxCiAgICBpNjQuZXh0ZW5kX2kzMl91CiAgICBpNjQuY29uc3QgNDgKICAgIGk2NC5zaGwKICAgIGk2NC5jb25zdCA0OAogICAgaTY0LnNocl9zCiAgICBsb2NhbC5nZXQgMAogICAgaTY0LmV4dGVuZF9pMzJfdQogICAgaTY0LmNvbnN0IDU2CiAgICBpNjQuc2hsCiAgICBpNjQuY29uc3QgNTYKICAgIGk2NC5zaHJfcwogICAgaTY0LmFkZAogICAgbG9jYWwuZ2V0IDIKICAgIGk2NC5leHRlbmRfaTMyX3MKICAgIGk2NC5hZGQKICAgIGxvY2FsLmdldCAzCiAgICBpNjQuYWRkCiAgICBsb2NhbC5nZXQgNAogICAgaTY0Lmd0X3MpCiAgKHRhYmxlICg7MDspIDEgMSBmdW5jcmVmKQogIChtZW1vcnkgKDswOykgMTYpCiAgKGdsb2JhbCAkX19zdGFja19wb2ludGVyIChtdXQgaTMyKSAoaTMyLmNvbnN0IDEwNDg1NzYpKQogIChnbG9iYWwgKDsxOykgaTMyIChpMzIuY29uc3QgMTA0ODU3NikpCiAgKGdsb2JhbCAoOzI7KSBpMzIgKGkzMi5jb25zdCAxMDQ4NTc2KSkKICAoZXhwb3J0ICJtZW1vcnkiIChtZW1vcnkgMCkpCiAgKGV4cG9ydCAibXVsdGlwbGVfY29sdW1ucyIgKGZ1bmMgJG11bHRpcGxlX2NvbHVtbnMpKQogIChleHBvcnQgIl9fZGF0YV9lbmQiIChnbG9iYWwgMSkpCiAgKGV4cG9ydCAiX19oZWFwX2Jhc2UiIChnbG9iYWwgMikpKQ=="
arg_types = [DataType.INT8, DataType.INT16,
             DataType.INT32, DataType.INT64, DataType.INT64]
utility.create_function("multiple_columns", wat_body_base64, arg_types)

################################################################################
# 5. search, query, and hybrid search
# After data were inserted into Milvus and indexed, you can perform:
# - search based on vector similarity
# - query based on scalar filtering(boolean, int, etc.)
# - hybrid search based on vector similarity and scalar filtering.

# Before conducting a search or a query, you need to load the data in `hello_milvus_udf` into memory.
print(fmt.format("Start loading"))
hello_milvus_udf.load()

# -----------------------------------------------------------------------------
# search based on vector similarity
print(fmt.format("Start searching based on vector similarity"))
vectors_to_search = entities[-1][-2:]
search_params = {
    "metric_type": "L2",
    "params": {"nprobe": 10},
}

start_time = time.time()
result = hello_milvus_udf.search(
    vectors_to_search, "embeddings", search_params, limit=3, output_fields=["random", "age64"])
end_time = time.time()

for hits in result:
    for hit in hits:
        print(
            f"hit: {hit}, random field: {hit.entity.get('random')}, age64 field: {hit.entity.get('age64')}")
print(search_latency_fmt.format(end_time - start_time))

# -----------------------------------------------------------------------------
# hybrid search
print(fmt.format("Start hybrid searching with `age64 > 1000`"))

start_time = time.time()
result = hello_milvus_udf.search(vectors_to_search, "embeddings", search_params,
                                 limit=3, expr="age64 > 1000", output_fields=["random", "age64"])
end_time = time.time()

for hits in result:
    for hit in hits:
        print(
            f"hit: {hit}, random field: {hit.entity.get('random')}, age64 field: {hit.entity.get('age64')}")
print(search_latency_fmt.format(end_time - start_time))

###############################################################################
# -----------------------------------------------------------------------------
# hybrid search by udf
print(fmt.format(
    "Start hybrid searching with `age64 > 1000` by UDF 'greater_than' [age64, 1000]"))

start_time = time.time()
result = hello_milvus_udf.search(vectors_to_search, "embeddings", search_params, limit=3,
                                 expr="UDF \"greater_than\" [age64, 1000]", output_fields=["random", "age64"])
end_time = time.time()

for hits in result:
    for hit in hits:
        print(
            f"hit: {hit}, random field: {hit.entity.get('random')}, age64 field: {hit.entity.get('age64')}")
print(search_latency_fmt.format(end_time - start_time))

###############################################################################
print(fmt.format(
    "Start hybrid searching with `UDF 'multiple_columns' [age8, age16, age32, age64, 4000]`"))

start_time = time.time()
result = hello_milvus_udf.query(expr="UDF \"multiple_columns\" [age8, age16, age32, age64, 4000]", output_fields=[
                                "random", "age8", "age16", "age32", "age64", "embeddings"])
end_time = time.time()

print(f"query result:\n-{result[0]}")
print(search_latency_fmt.format(end_time - start_time))


###############################################################################
# 6. delete function
# utility.drop_function("greater_than")
# utility.drop_function("multiple_columns")

###############################################################################
# 6. delete entities by PK
# You can delete entities by their PK values using boolean expressions.
ids = insert_result.primary_keys

expr = f'pk in ["{ids[0]}" , "{ids[1]}"]'
print(fmt.format(f"Start deleting with expr `{expr}`"))

result = hello_milvus_udf.query(
    expr=expr, output_fields=["random", "embeddings"])
print(
    f"query before delete by expr=`{expr}` -> result: \n-{result[0]}\n-{result[1]}\n")

hello_milvus_udf.delete(expr)

result = hello_milvus_udf.query(
    expr=expr, output_fields=["random", "embeddings"])
print(f"query after delete by expr=`{expr}` -> result: {result}\n")


###############################################################################
# 7. drop collection
# Finally, drop the hello_milvus_udf collection
print(fmt.format("Drop collection `hello_milvus_udf`"))
utility.drop_collection("hello_milvus_udf")
