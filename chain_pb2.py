# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: chain.proto
"""Generated protocol buffer code."""
from google.protobuf.internal import builder as _builder
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x0b\x63hain.proto\"\x0e\n\x0cProbeRequest\"\x1d\n\rProbeResponse\x12\x0c\n\x04name\x18\x01 \x01(\t\"\x10\n\x0eProcessRequest\"$\n\x0fProcessResponse\x12\x11\n\tprocesses\x18\x01 \x03(\t\"\x0f\n\rChainResponse\"!\n\x0c\x43hainRequest\x12\x11\n\tprocesses\x18\x01 \x03(\t\"\x12\n\x10SendBookResponse\"?\n\x0fSendBookRequest\x12\x0f\n\x07process\x18\x01 \x01(\t\x12\x0c\n\x04\x62ook\x18\x02 \x01(\t\x12\r\n\x05price\x18\x03 \x01(\t\"#\n\x10ListBooksRequest\x12\x0f\n\x07process\x18\x01 \x01(\t\"\"\n\x11ListBooksResponse\x12\r\n\x05\x62ooks\x18\x01 \x03(\t\",\n\x0b\x42ookRequest\x12\x0f\n\x07process\x18\x01 \x01(\t\x12\x0c\n\x04\x62ook\x18\x02 \x01(\t\"0\n\x0c\x42ookResponse\x12\r\n\x05price\x18\x01 \x01(\t\x12\x11\n\told_price\x18\x02 \x01(\t2\xa8\x02\n\x05\x43hain\x12(\n\x05Probe\x12\r.ProbeRequest\x1a\x0e.ProbeResponse\"\x00\x12\x30\n\tProcesses\x12\x0f.ProcessRequest\x1a\x10.ProcessResponse\"\x00\x12+\n\x08SetChain\x12\r.ChainRequest\x1a\x0e.ChainResponse\"\x00\x12\x31\n\x08SendBook\x12\x10.SendBookRequest\x1a\x11.SendBookResponse\"\x00\x12\x34\n\tListBooks\x12\x11.ListBooksRequest\x1a\x12.ListBooksResponse\"\x00\x12-\n\x0cGetBookPrice\x12\x0c.BookRequest\x1a\r.BookResponse\"\x00\x62\x06proto3')

_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, globals())
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'chain_pb2', globals())
if _descriptor._USE_C_DESCRIPTORS == False:

  DESCRIPTOR._options = None
  _PROBEREQUEST._serialized_start=15
  _PROBEREQUEST._serialized_end=29
  _PROBERESPONSE._serialized_start=31
  _PROBERESPONSE._serialized_end=60
  _PROCESSREQUEST._serialized_start=62
  _PROCESSREQUEST._serialized_end=78
  _PROCESSRESPONSE._serialized_start=80
  _PROCESSRESPONSE._serialized_end=116
  _CHAINRESPONSE._serialized_start=118
  _CHAINRESPONSE._serialized_end=133
  _CHAINREQUEST._serialized_start=135
  _CHAINREQUEST._serialized_end=168
  _SENDBOOKRESPONSE._serialized_start=170
  _SENDBOOKRESPONSE._serialized_end=188
  _SENDBOOKREQUEST._serialized_start=190
  _SENDBOOKREQUEST._serialized_end=253
  _LISTBOOKSREQUEST._serialized_start=255
  _LISTBOOKSREQUEST._serialized_end=290
  _LISTBOOKSRESPONSE._serialized_start=292
  _LISTBOOKSRESPONSE._serialized_end=326
  _BOOKREQUEST._serialized_start=328
  _BOOKREQUEST._serialized_end=372
  _BOOKRESPONSE._serialized_start=374
  _BOOKRESPONSE._serialized_end=422
  _CHAIN._serialized_start=425
  _CHAIN._serialized_end=721
# @@protoc_insertion_point(module_scope)
