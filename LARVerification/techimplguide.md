
# Technical Implementation Guide: LAR Verification Multi-Agent System

## Architecture Overview: Strands Agents + Bedrock AgentCore

This guide provides a production-ready implementation using **Strands Agents framework** deployed on **Amazon Bedrock AgentCore Runtime** for the simplified LAR verification system.

---

## Multi-Agent Architecture Design

### Agent 1: Orchestrator Agent
**Framework**: Strands Agents with AgentCore Runtime  
**Deployment**: Serverless HTTP service via AgentCore

```python
from strands import Agent, tool
from bedrock_agentcore_runtime import AgentCoreRuntime

class OrchestratorAgent(Agent):
    """Coordinates workflow and manages user interaction"""

    system_prompt = """You are the LAR Verification Orchestrator.
    Extract AWB numbers, coordinate validation workflow, and present results."""

    @tool
    def parse_user_request(self, user_input: str) -> dict:
        """Extract AWB number and validation intent"""
        # Extract AWB pattern (8 digits)
        import re
        awb_match = re.search(r'\b\d{8}\b', user_input)
        return {
            "awb_number": awb_match.group(0) if awb_match else None,
            "intent": "validate_lar"
        }

    @tool
    def present_results(self, validation_result: dict) -> str:
        """Format validation results for user"""
        if validation_result["status"] == "PASS":
            return f"✓ LAR validated for AWB {validation_result['awb']}. Document {validation_result['doc_version']} compliant. Checksheet updated."
        else:
            return f"✗ Validation failed: {validation_result['reason']}"
```

---

### Agent 2: Shipment Context Agent
**Purpose**: Retrieves shipment data via API integration

```python
class ShipmentContextAgent(Agent):
    """Fetches and validates shipment information"""

    system_prompt = """You retrieve shipment details and determine LAR applicability."""

    @tool
    def fetch_shipment_data(self, awb_number: str) -> dict:
        """Call Shipment API to get AWB details"""
        import requests

        response = requests.get(
            f"api.icargo.com/v1/shipments/{awb_number}",
            headers={"Authorization": "Bearer {token}"}
        )

        if response.status_code == 200:
            data = response.json()
            return {
                "awb": awb_number,
                "product": data.get("product_code"),
                "commodity": data.get("commodity_code"),
                "handling_codes": data.get("handling_codes", []),
                "origin": data.get("origin"),
                "destination": data.get("destination")
            }
        return {"error": "AWB not found"}

    @tool
    def check_lar_required(self, shipment_data: dict) -> bool:
        """Determine if LAR validation is needed"""
        return "LAR" in shipment_data.get("handling_codes", [])
```

---

### Agent 3: Document Retrieval Agent
**Purpose**: Locates regulatory documents from Share Drive

```python
class DocumentRetrievalAgent(Agent):
    """Searches for LAR documents in repository"""

    system_prompt = """You locate and verify LAR documents from the Share Drive."""

    @tool
    def find_lar_document(self, shipment_context: dict) -> dict:
        """Query Share Drive for LAR documents"""
        import boto3

        s3_client = boto3.client('s3')
        bucket = "icargo-share-drive"
        prefix = "regulatory/LAR/"

        try:
            response = s3_client.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix
            )

            if response.get('Contents'):
                latest_doc = sorted(
                    response['Contents'],
                    key=lambda x: x['LastModified'],
                    reverse=True
                )[0]

                return {
                    "found": True,
                    "document_key": latest_doc['Key'],
                    "version": self._extract_version(latest_doc['Key']),
                    "last_modified": latest_doc['LastModified'].isoformat()
                }

            return {"found": False, "reason": "LAR document not found"}

        except Exception as e:
            return {"found": False, "reason": f"Access error: {str(e)}"}

    def _extract_version(self, key: str) -> str:
        """Extract version from filename"""
        import re
        match = re.search(r'v(\d+\.\d+)', key)
        return match.group(0) if match else "unknown"
```

---

### Agent 4: Validation Agent
**Purpose**: Performs compliance validation logic

```python
class ValidationAgent(Agent):
    """Executes LAR compliance validation"""

    system_prompt = """You validate LAR documents against checksheet rules."""

    @tool
    def validate_compliance(self, shipment_data: dict, document_data: dict) -> dict:
        """Apply validation rules"""

        if not document_data.get("found"):
            return {
                "status": "FAIL",
                "reason": document_data.get("reason", "Document missing")
            }

        # Simple validation rules
        validation_checks = {
            "document_present": document_data["found"],
            "version_valid": self._check_version(document_data["version"]),
            "commodity_match": self._validate_commodity(shipment_data)
        }

        all_passed = all(validation_checks.values())

        return {
            "status": "PASS" if all_passed else "FAIL",
            "checks": validation_checks,
            "doc_version": document_data.get("version"),
            "awb": shipment_data["awb"]
        }

    def _check_version(self, version: str) -> bool:
        """Verify document version is current"""
        # Simplified: check if version >= 2.0
        try:
            ver_num = float(version.replace('v', ''))
            return ver_num >= 2.0
        except:
            return False

    def _validate_commodity(self, shipment_data: dict) -> bool:
        """Check commodity code against LAR requirements"""
        # Simplified: assume live animals have commodity starting with 'AVI'
        return shipment_data.get("commodity", "").startswith("AVI")
```

---

### Agent 5: Status Management Agent
**Purpose**: Updates checksheet status via API

```python
class StatusManagementAgent(Agent):
    """Updates checksheet verification status"""

    system_prompt = """You update checksheet status after successful validation."""

    @tool
    def update_checksheet(self, awb_number: str, validation_result: dict) -> dict:
        """Call Checksheet API to mark as verified"""
        import requests

        if validation_result["status"] != "PASS":
            return {"updated": False, "reason": "Validation failed"}

        response = requests.post(
            "api.icargo.com/v1/checksheets/update",
            json={
                "awb_number": awb_number,
                "checksheet_type": "LAR",
                "status": "VERIFIED",
                "validated_at": self._get_timestamp(),
                "validation_details": validation_result
            },
            headers={"Authorization": "Bearer {token}"}
        )

        return {
            "updated": response.status_code == 200,
            "checksheet_id": response.json().get("checksheet_id")
        }

    def _get_timestamp(self) -> str:
        from datetime import datetime
        return datetime.utcnow().isoformat()
```

---

## Deployment Configuration

### AgentCore Runtime Deployment

```python
# deploy_to_agentcore.py
from bedrock_agentcore_runtime import deploy_agent

# Deploy orchestrator as main entry point
deploy_agent(
    agent=OrchestratorAgent(),
    runtime_config={
        "memory_enabled": True,  # Enable conversation memory
        "code_interpreter": False,  # Not needed for this use case
        "observability": True,  # Enable CloudWatch logging
        "timeout_seconds": 30
    },
    aws_config={
        "region": "us-east-1",
        "execution_role": "arn:aws:iam::account:role/AgentCoreRole"
    }
)
```

---

### Multi-Agent Orchestration Flow

```python
# main_workflow.py
async def execute_lar_validation(user_input: str):
    """Main workflow coordinating all agents"""

    # Step 1: Parse request
    orchestrator = OrchestratorAgent()
    request_data = orchestrator.parse_user_request(user_input)

    if not request_data["awb_number"]:
        return "Please provide a valid AWB number"

    # Step 2: Fetch shipment data
    shipment_agent = ShipmentContextAgent()
    shipment_data = shipment_agent.fetch_shipment_data(request_data["awb_number"])

    if "error" in shipment_data:
        return f"AWB not found - please verify number"

    # Step 3: Check if LAR required
    if not shipment_agent.check_lar_required(shipment_data):
        return "LAR validation not required for this shipment"

    # Step 4: Retrieve document
    doc_agent = DocumentRetrievalAgent()
    document_data = doc_agent.find_lar_document(shipment_data)

    # Step 5: Validate compliance
    validation_agent = ValidationAgent()
    validation_result = validation_agent.validate_compliance(
        shipment_data,
        document_data
    )

    # Step 6: Update checksheet if passed
    if validation_result["status"] == "PASS":
        status_agent = StatusManagementAgent()
        status_agent.update_checksheet(
            request_data["awb_number"],
            validation_result
        )

    # Step 7: Present results
    return orchestrator.present_results(validation_result)
```

---

## Required Datasets Schema

### Dataset 1: Shipment Master (DynamoDB/RDS)
```json
{
  "awb_number": "12345678",
  "product_code": "GEN",
  "commodity_code": "AVI001",
  "handling_codes": ["LAR", "AVI"],
  "origin": "JFK",
  "destination": "LHR",
  "status": "PENDING"
}
```

### Dataset 2: Document Repository (S3 Metadata)
```json
{
  "document_id": "LAR_v2.3",
  "document_type": "LAR",
  "s3_key": "regulatory/LAR/LAR_v2.3.pdf",
  "version": "2.3",
  "last_updated": "2026-01-15T10:00:00Z",
  "validity_period": "2026-12-31"
}
```

### Dataset 3: Checksheet Configuration (DynamoDB)
```json
{
  "checksheet_id": "CS_LAR_001",
  "handling_code": "LAR",
  "required_documents": ["LAR"],
  "validation_rules": {
    "document_version_min": "2.0",
    "commodity_prefix": "AVI"
  },
  "status": "PENDING"
}
```

### Dataset 4: Validation Rules Matrix (DynamoDB)
```json
{
  "rule_id": "LAR_001",
  "handling_code": "LAR",
  "required_documents": ["LAR"],
  "commodity_requirements": {
    "prefix": "AVI",
    "description": "Live Animals"
  },
  "version_requirements": {
    "minimum_version": "2.0"
  }
}
```

---

## Implementation Timeline (2-3 Hours)

### Hour 1: Core Agent Development
- **0:00-0:30**: Implement Orchestrator + Shipment Context Agent
- **0:30-1:00**: Implement Document Retrieval Agent

### Hour 2: Validation & Integration
- **1:00-1:20**: Implement Validation Agent
- **1:20-1:40**: Implement Status Management Agent
- **1:40-2:00**: Wire multi-agent workflow

### Hour 3: Deployment & Testing
- **2:00-2:30**: Deploy to AgentCore Runtime
- **2:30-3:00**: Integration testing with mock APIs

---

## Testing Strategy

```python
# test_workflow.py
import pytest
from main_workflow import execute_lar_validation

def test_successful_validation():
    """Test complete validation workflow"""
    result = execute_lar_validation("Validate LAR for AWB 12345678")
    assert "✓ LAR validated" in result
    assert "Checksheet updated" in result

def test_missing_document():
    """Test handling of missing LAR document"""
    result = execute_lar_validation("Validate LAR for AWB 99999999")
    assert "Validation failed" in result
    assert "Document missing" in result

def test_invalid_awb():
    """Test handling of invalid AWB number"""
    result = execute_lar_validation("Validate LAR for AWB invalid")
    assert "Please provide a valid AWB number" in result

def test_lar_not_required():
    """Test shipment without LAR handling code"""
    result = execute_lar_validation("Validate LAR for AWB 87654321")
    assert "LAR validation not required" in result
```

---

## Key Architecture Benefits

### Strands Agents + Bedrock AgentCore Advantages
- **Serverless scaling**: AgentCore handles infrastructure automatically
- **Modular development**: Each agent can be developed/tested independently
- **Secure execution**: Built-in AWS IAM integration
- **Observability**: CloudWatch logging for debugging
- **Framework flexibility**: Strands Agents provides model-driven approach
- **Cost efficiency**: Pay only for actual execution time
- **Production-ready**: Enterprise-grade runtime with memory and monitoring

---

## Simplified Scope

### Included Features
- Single handling code validation (LAR only)
- Basic document presence check
- Simple pass/fail validation logic
- Chat-based user interaction
- Checksheet status update
- AWS S3 document retrieval
- API-based shipment data fetch

### Excluded (Future Enhancement)
- Multiple simultaneous handling codes
- Complex document content parsing
- Real-time document version comparison
- Advanced audit trail logging
- Rollback mechanisms
- Multi-language support
- Advanced error recovery

---

## Success Metrics

### Performance Targets
- Validation completes in < 10 seconds
- 100% detection of missing LAR documents
- Zero false positives for compliant shipments
- User receives clear pass/fail result

### Operational Metrics
- Reduction in documentation-related shipment failures
- Time saved per validation (vs. manual process)
- User satisfaction score
- System uptime and reliability

---

## Edge Case Handling

| Edge Case | Handling Strategy |
|-----------|------------------|
| Missing LAR document | Return "Validation Failed - LAR document not found" |
| API failure | Return "Unable to validate - system error, please retry" |
| Invalid AWB | Return "AWB not found - please verify number" |
| Outdated document version | Return "Validation Failed - Document version outdated" |
| S3 access denied | Return "Unable to access document repository" |
| Multiple LAR documents | Select most recent by timestamp |
| Network timeout | Implement retry logic with exponential backoff |

---

## Security Considerations

### Authentication & Authorization
- AWS IAM roles for AgentCore execution
- API token-based authentication for iCargo APIs
- S3 bucket policies for document access
- User-level permissions for checksheet updates

### Data Protection
- Encryption in transit (TLS 1.3)
- Encryption at rest (S3 server-side encryption)
- No sensitive data in logs
- Audit trail for compliance

---

## Deployment Checklist

- [ ] Configure AWS IAM roles for AgentCore
- [ ] Set up S3 bucket for LAR documents
- [ ] Configure API endpoints for Shipment and Checksheet APIs
- [ ] Deploy agents to AgentCore Runtime
- [ ] Enable CloudWatch logging
- [ ] Configure environment variables (API tokens, bucket names)
- [ ] Run integration tests
- [ ] Set up monitoring dashboards
- [ ] Document API endpoints and credentials
- [ ] Train users on chat interface

---

## Next Steps

1. **Set up AWS environment**: Create IAM roles, S3 buckets, and API Gateway
2. **Implement mock APIs**: Create test endpoints for Shipment and Checksheet APIs
3. **Deploy agents**: Use AgentCore CLI to deploy all five agents
4. **Integration testing**: Validate end-to-end workflow with test data
5. **User acceptance testing**: Gather feedback from cargo operations team
6. **Production rollout**: Deploy to production environment with monitoring

---

## References

- Strands Agents Documentation: strandsagents.com/latest/documentation/
- Amazon Bedrock AgentCore: docs.aws.amazon.com/bedrock-agentcore/
- AWS IAM Best Practices: docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html
- IATA LAR Standards: iata.org/en/programs/cargo/live-animals/

---

**Document Version**: 1.0  
**Last Updated**: January 18, 2026  
**Author**: LAR Verification Implementation Team
