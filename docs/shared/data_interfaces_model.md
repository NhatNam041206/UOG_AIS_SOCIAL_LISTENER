# Module: data_interfaces_model

## Architectural Role
Model boundary for shared schema and data-access contracts.

## Core Functional Objective
Centralizes schema templates, mapper interfaces, and dataframe providers for cross-phase record handling.

## Class and Method Signatures
* `RecordSchemaTemplate`: Abstract schema contract describing required fields and validation behavior.
  * `required_fields(self) -> List[str]`: Return the mandatory column names expected by downstream modules.
  * `validate(self, record: Dict[str, Any]) -> bool`: Return True when an input record conforms to the schema template.
* `SchemaMapperInterface`: Abstract mapper for normalizing raw provider payloads into shared schema format.
  * `map_record(self, raw_record: Dict[str, Any]) -> Dict[str, Any]`: Transform one raw record into the canonical schema representation.
* `DataFrameProvider`: Abstract provider for exposing typed tabular datasets to controllers.
  * `load(self, source: str, options: Optional[Dict[str, Any]] = None) -> Any`: Load source data into a DataFrame-like object.
