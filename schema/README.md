# API schema returned from a Tessera SX40 v3.5.2
### Querying a processor with the ```?help=1``` flag returns a handy, human readable, schema for reference.
```bash
curl -s 'http://192.0.2.50/api/?help=1' | jq . > schema_tessera_3.5.2.json
```

This is identical across two SX40 units (serials 010127 & 022582) on software 3.5.2, but I have not yet been able to test against other processors in the product line.
```bash
    diff <(jq -S . unit-a.json) <(jq -S . unit-b.json)
    
    # no output
```