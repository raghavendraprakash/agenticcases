## Simplified Agentic Case

### Core Problem Statement

Enable cargo operations agents to validate IATA Live Animal Regulations (LAR) documents through a chat interface before shipment execution, preventing late-stage compliance failures.

---

## Multi-Agent Architecture

### Agent 1: Shipment Context Agent

**Role:** Retrieves and validates shipment information

**Input:** AWB Number from user

**Actions:**
- Fetch shipment details via Shipment API (Product, Handling Codes, Commodity)
- Determine if LAR validation is required (check for LAR handling code)
- Pass validated context to next agent

**Output:** Structured shipment context object

---

### Agent 2: Document Retrieval Agent

**Role:** Locates required regulatory documents

**Input:** Shipment context from Agent 1

**Actions:**
- Query iCargo Share Drive for LAR documents
- Check document availability and version
- Return document status (Found/Missing/Outdated)

**Output:** Document metadata and availability status

---

### Agent 3: Validation Agent

**Role:** Performs compliance validation

**Input:** Shipment context + Document status

**Actions:**
- Apply checksheet validation rules
- Cross-check document requirements against shipment attributes
- Generate validation result (Pass/Fail with reasons)

**Output:** Validation report with compliance status

---

### Agent 4: Orchestrator Agent

**Role:** Coordinates workflow and user interaction

**Input:** User query via chat

**Actions:**
- Parse user intent and extract AWB number
- Coordinate Agent 1 → Agent 2 → Agent 3 sequence
- Present results to user in chat
- Handle user confirmation
- Trigger Checksheet API update on success

**Output:** User-friendly validation summary and system updates

---

## Simplified Workflow

1. User initiates: `"Validate LAR for AWB 12345678"`
2. Orchestrator extracts AWB number
3. Shipment Context Agent fetches shipment data
4. Document Retrieval Agent checks for LAR documents
5. Validation Agent performs compliance check
6. Orchestrator presents results: `"✓ LAR validated. Document v2.3 compliant. Checksheet updated."`
7. User confirms (optional)
8. System marks checksheet as verified via API

---

## Required Datasets

### Dataset 1: Shipment Master Data

- **AWB Number** (primary key)
- **Product Code**
- **Commodity Code**
- **Handling Codes** (array)
- **Origin/Destination airports**
- **Shipment status**

### Dataset 2: Regulatory Document Repository

- **Document ID**
- **Document Type** (LAR, DGR, etc.)
- **Version number**
- **File path/URL**
- **Last updated timestamp**
- **Validity period**

### Dataset 3: Checksheet Configuration

- **Checksheet ID**
- **Applicable handling codes**
- **Required documents**
- **Validation rules** (JSON format)
- **Status** (Pending/Verified/Failed)

### Dataset 4: Validation Rules Matrix

- **Handling Code → Required Documents** mapping
- **Product Type → Regulatory requirements**
- **Commodity → Special validations**

---

## Implementation Scope (2-3 Hours)

### Included

- Single handling code validation (LAR only)
- Basic document presence check
- Simple pass/fail validation logic
- Chat-based user interaction
- Checksheet status update

### Excluded (Future Enhancement)

- Multiple simultaneous handling codes
- Complex document content parsing
- Real-time document version comparison
- Advanced audit trail logging
- Rollback mechanisms

---

## Success Metrics (Simplified)

- Validation completes in < 10 seconds
- 100% detection of missing LAR documents
- Zero false positives for compliant shipments
- User receives clear pass/fail result

---

## Edge Case Handling (Simplified)

| Scenario | Response |
|----------|----------|
| Missing document | `"Validation Failed - LAR document not found"` |
| API failure | `"Unable to validate - system error, please retry"` |
| Invalid AWB | `"AWB not found - please verify number"` |

---
