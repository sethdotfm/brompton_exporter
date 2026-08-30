# API schema returned from a Tessera SX40 v3.5.2
### Querying a processor with the ```?help=1``` flag returns a handy, human readable, schema for reference.
```bash
curl -s 'http://192.0.2.50/api/?help=1' | jq . > schema_tessera_3.5.2.json
```