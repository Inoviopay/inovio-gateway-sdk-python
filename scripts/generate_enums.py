#!/usr/bin/env python3
"""Generate src/inovio_gateway/enums/generated.py from ../spec/spec-enums.json.

Decision D1: enums come from one machine-readable spec artifact, not hand-copied
per language. Do not edit the generated file — edit the spec extract and re-run.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = HERE.parent.parent / "spec" / "spec-enums.json"
OUT = HERE.parent / "src" / "inovio_gateway" / "enums" / "generated.py"

spec = json.loads(SPEC.read_text())
A = spec["appendices"]
ver = spec["apiVersion"]

L = []
w = L.append
w('"""GENERATED FILE — DO NOT EDIT.')
w("")
w(f"Source: Inovio Gateway Payments Service API v{ver} (api-sdk/spec/spec-enums.json)")
w("Regenerate: python scripts/generate_enums.py")
w("")
w("Classifiers (retryable/terminal/stopRecurring, AVS/CVV classification and the")
w("API-code -> exception mapping) are DERIVED by the SDK project, not stated in")
w('the spec. See api-sdk/spec/README.md.')
w('"""')
w("from __future__ import annotations")
w("")
w("from dataclasses import dataclass")
w("from enum import Enum")
w("from typing import Dict")
w("")
w("")
w(f'SPEC_API_VERSION = "{ver}"')
w("")
w("")
w("class TransactionStatus(str, Enum):")
w('    """Appendix B — the master transaction lifecycle (5 states)."""')
for e in A["B_transactionStatus"]:
    w(f'    {e["code"]} = "{e["code"]}"')
w("")
w("")
w("TRANSACTION_STATUS_DESCRIPTIONS: Dict[TransactionStatus, str] = {")
for e in A["B_transactionStatus"]:
    w(f'    TransactionStatus.{e["code"]}: {json.dumps(e["description"])},')
w("}")
w("")
w("")
w("class RequestAction(str, Enum):")
w('    """Appendix A — every REQUEST_ACTION the gateway accepts."""')
for e in A["A_serviceRequestTypes"]:
    w(f'    {e["code"]} = "{e["code"]}"')
w("")
w("")
w("@dataclass(frozen=True)")
w("class ServiceResponseCodeInfo:")
w("    code: int")
w("    description: str")
w("    retryable: bool")
w("    stop_recurring: bool")
w("    approval: bool")
w("    terminal: bool")
w("")
w("")
w("SERVICE_RESPONSE_CODES: Dict[int, ServiceResponseCodeInfo] = {")
for e in A["D_serviceResponseCodes"]:
    w(f'    {e["code"]}: ServiceResponseCodeInfo({e["code"]}, {json.dumps(e["description"])}, '
      f'{e["retryable"]}, {e["stopRecurring"]}, {e["approval"]}, {e["terminal"]}),')
w("}")
w("")
w("")
w("@dataclass(frozen=True)")
w("class ApiResponseCodeInfo:")
w("    code: int")
w("    description: str")
w("    recommendation: str")
w("    maps_to_exception: str")
w("    carries_ref_field: bool")
w("")
w("")
w("API_RESPONSE_CODES: Dict[int, ApiResponseCodeInfo] = {")
for e in A["C_apiResponseCodes"]:
    w(f'    {e["code"]}: ApiResponseCodeInfo({e["code"]}, {json.dumps(e["description"])}, '
      f'{json.dumps(e["recommendation"])}, {json.dumps(e["mapsToException"])}, {e["carriesRefField"]}),')
w("}")
w("")
w("")
w("@dataclass(frozen=True)")
w("class AvsCodeInfo:")
w("    code: str")
w("    description: str")
w("    card_network: str")
w("    #: DERIVED. 'partial' means some elements matched and some did not. Whether")
w("    #: that is acceptable is a merchant risk-policy decision, not a spec fact.")
w("    classification: str")
w("")
w("")
w("AVS_CODES: Dict[str, AvsCodeInfo] = {")
for e in A["E_avsCodes"]:
    w(f'    {json.dumps(e["code"])}: AvsCodeInfo({json.dumps(e["code"])}, {json.dumps(e["description"])}, '
      f'{json.dumps(e["cardNetwork"])}, {json.dumps(e["classification"])}),')
w("}")
w("")
w("")
w("@dataclass(frozen=True)")
w("class CvvCodeInfo:")
w("    code: str")
w("    description: str")
w("    classification: str")
w("")
w("")
w("CVV_CODES: Dict[str, CvvCodeInfo] = {")
for e in A["F_cvvCodes"]:
    w(f'    {json.dumps(e["code"])}: CvvCodeInfo({json.dumps(e["code"])}, {json.dumps(e["description"])}, '
      f'{json.dumps(e["classification"])}),')
w("}")
w("")

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(L))
n = sum(len(v) for v in A.values())
print(f"generated {OUT} ({n} enum values from spec v{ver})")
