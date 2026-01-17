# Bedrock AgentCore Deployment Guide

## Overview

This guide provides step-by-step instructions for deploying the Flight Cargo Assessment System to AWS Bedrock AgentCore. The deployment creates a fully managed, scalable, and production-ready AI agent service.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    AWS Bedrock AgentCore                        │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌──────────────────┐                   │
│  │ Bedrock Agent   │    │ Lambda Executor  │                   │
│  │ (Claude 3.5)    │◄──►│ (Python 3.11)   │                   │
│  │                 │    │                  │                   │
│  └─────────────────┘    └──────────────────┘                   │
│           │                       │                            │
│           ▼                       ▼                            │
│  ┌─────────────────┐    ┌──────────────────┐                   │
│  │ Knowledge Base  │    │ S3 Artifacts     │                   │
│  │ (Aircraft Specs)│    │ (Code & Deps)    │                   │
│  └─────────────────┘    └──────────────────┘                   │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ CloudWatch      │
                  │ (Monitoring)    │
                  └─────────────────┘
```

## Prerequisites

### 1. AWS Account Setup
- AWS account with appropriate permissions
- AWS CLI configured with credentials
- Bedrock service enabled in your region

### 2. Required Permissions
Your AWS user/role needs these permissions:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:*",
                "bedrock-agent:*",
                "lambda:*",
                "iam:*",
                "s3:*",
                "cloudformation:*",
                "logs:*",
                "sns:*",
                "sqs:*"
            ],
            "Resource": "*"
        }
    ]
}
```

### 3. Local Environment
- Python 3.11+
- AWS CLI v2
- Required Python packages (see requirements.txt)

## Deployment Methods

### Method 1: Automated Deployment (Recommended)

#### Step 1: Validate Prerequisites
```bash
python deploy_to_agentcore.py --validate-only --region us-east-1
```

#### Step 2: Deploy to Production
```bash
python deploy_to_agentcore.py --region us-east-1 --environment production
```

#### Step 3: Test Deployment
```bash
python test_deployed_agent.py --region us-east-1 --test all
```

### Method 2: CloudFormation Deployment

#### Step 1: Package Dependencies
```bash
# Create dependencies layer
mkdir -p python
pip install -r requirements.txt -t python/
zip -r dependencies_layer.zip python/

# Package application code
zip -r agent_application.zip lambda_handler.py flight_cargo_assessment/
```

#### Step 2: Deploy CloudFormation Stack
```bash
aws cloudformation create-stack \
    --stack-name flight-cargo-assessment-production \
    --template-body file://bedrock_agentcore_cloudformation.yaml \
    --parameters ParameterKey=Environment,ParameterValue=production \
    --capabilities CAPABILITY_NAMED_IAM \
    --region us-east-1
```

#### Step 3: Upload Artifacts
```bash
# Get bucket name from stack outputs
BUCKET_NAME=$(aws cloudformation describe-stacks \
    --stack-name flight-cargo-assessment-production \
    --query 'Stacks[0].Outputs[?OutputKey==`S3BucketName`].OutputValue' \
    --output text)

# Upload packages
aws s3 cp dependencies_layer.zip s3://$BUCKET_NAME/layers/
aws s3 cp agent_application.zip s3://$BUCKET_NAME/code/
```

### Method 3: Manual Deployment

#### Step 1: Create IAM Roles
```bash
# Create agent role
aws iam create-role \
    --role-name flight-cargo-assessment-agent-role \
    --assume-role-policy-document file://agent_trust_policy.json

# Attach policies
aws iam attach-role-policy \
    --role-name flight-cargo-assessment-agent-role \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonBedrockAgentServiceRolePolicy
```

#### Step 2: Create S3 Bucket
```bash
aws s3 mb s3://bedrock-agent-flight-cargo-assessment-us-east-1
```

#### Step 3: Create Lambda Function
```bash
aws lambda create-function \
    --function-name flight-cargo-assessment-executor \
    --runtime python3.11 \
    --role arn:aws:iam::ACCOUNT:role/lambda-execution-role \
    --handler lambda_handler.handler \
    --zip-file fileb://agent_application.zip
```

#### Step 4: Create Bedrock Agent
```bash
python bedrock_agentcore_deployment.py
```

## Configuration

### Environment Variables
Set these environment variables for the Lambda function:
```bash
CARGO_AGENT_MODE=ai_powered
AWS_REGION=us-east-1
LOG_LEVEL=INFO
```

### Agent Configuration
The agent is configured with:
- **Foundation Model**: Claude 3.5 Sonnet
- **Session Timeout**: 30 minutes
- **Memory**: 512 MB
- **Timeout**: 5 minutes

### Action Groups
The agent includes these action groups:
1. **cargo-assessment**: Core cargo assessment functions
2. **capacity-management**: Capacity inquiry and monitoring
3. **system-status**: System health and configuration

## Testing

### Functional Tests
```bash
# Run all tests
python test_deployed_agent.py --test all

# Run specific tests
python test_deployed_agent.py --test cargo
python test_deployed_agent.py --test capacity
python test_deployed_agent.py --test performance
```

### Manual Testing via AWS Console
1. Open AWS Bedrock Console
2. Navigate to Agents
3. Select your agent
4. Use the test interface to send queries

### Example Test Queries

#### Cargo Assessment
```
Please assess this cargo:
- Dimensions: 2.0m × 1.5m × 1.2m
- Weight: 800 kg
- Type: electronics
- Fragile: yes
- Priority: high

Where should I place it?
```

#### Capacity Inquiry
```
What is the current capacity status of the aircraft?
```

#### Weight Balance Analysis
```
I need to place 5000 kg of machinery. What are the weight and balance implications?
```

## Monitoring and Maintenance

### CloudWatch Metrics
Monitor these key metrics:
- **Invocation Count**: Number of agent invocations
- **Error Rate**: Percentage of failed invocations
- **Duration**: Response time metrics
- **Throttles**: Rate limiting events

### CloudWatch Alarms
Configured alarms:
- High error rate (>5 errors in 5 minutes)
- High latency (>30 seconds average)
- Lambda function errors

### Log Analysis
Check logs in:
- `/aws/lambda/flight-cargo-assessment-executor`
- Bedrock Agent logs (if enabled)

### Performance Optimization
- Monitor response times
- Optimize Lambda memory allocation
- Review agent instruction efficiency
- Consider caching for repeated queries

## Troubleshooting

### Common Issues

#### 1. Agent Not Responding
**Symptoms**: No response or timeout errors
**Solutions**:
- Check Lambda function logs
- Verify IAM permissions
- Test Lambda function directly
- Check Bedrock service status

#### 2. Incorrect Responses
**Symptoms**: Agent gives wrong or incomplete answers
**Solutions**:
- Review agent instructions
- Check action group configuration
- Validate Lambda function logic
- Test with simpler queries

#### 3. High Latency
**Symptoms**: Slow response times
**Solutions**:
- Increase Lambda memory
- Optimize code performance
- Check network connectivity
- Review Bedrock model selection

#### 4. Permission Errors
**Symptoms**: Access denied errors
**Solutions**:
- Verify IAM roles and policies
- Check resource-based policies
- Validate cross-service permissions
- Review CloudFormation stack

### Debugging Commands

#### Check Stack Status
```bash
aws cloudformation describe-stacks \
    --stack-name flight-cargo-assessment-production
```

#### View Lambda Logs
```bash
aws logs tail /aws/lambda/flight-cargo-assessment-executor --follow
```

#### Test Lambda Function
```bash
aws lambda invoke \
    --function-name flight-cargo-assessment-executor \
    --payload file://test_payload.json \
    response.json
```

#### Check Agent Status
```bash
aws bedrock-agent get-agent --agent-id YOUR_AGENT_ID
```

## Cost Optimization

### Usage Patterns
- **Development**: Use smaller models, limit testing
- **Staging**: Moderate usage for integration testing
- **Production**: Full-scale deployment with monitoring

### Cost Monitoring
- Set up billing alerts
- Monitor Bedrock usage
- Track Lambda invocations
- Review S3 storage costs

### Optimization Strategies
- Use appropriate model sizes
- Implement caching where possible
- Optimize Lambda memory allocation
- Clean up unused resources

## Security Best Practices

### IAM Security
- Use least privilege principle
- Regularly rotate access keys
- Enable CloudTrail logging
- Monitor IAM usage

### Data Protection
- Encrypt data in transit and at rest
- Use VPC endpoints where applicable
- Implement proper access controls
- Regular security audits

### Network Security
- Use private subnets for Lambda
- Configure security groups properly
- Enable VPC Flow Logs
- Monitor network traffic

## Scaling and High Availability

### Auto Scaling
- Lambda automatically scales
- Monitor concurrent executions
- Set appropriate reserved concurrency
- Plan for traffic spikes

### Multi-Region Deployment
```bash
# Deploy to multiple regions
python deploy_to_agentcore.py --region us-east-1 --environment production
python deploy_to_agentcore.py --region eu-west-1 --environment production
```

### Disaster Recovery
- Regular backups of configuration
- Cross-region replication
- Automated failover procedures
- Recovery time objectives (RTO)

## Cleanup

### Remove Deployment
```bash
# Automated cleanup
python deploy_to_agentcore.py --cleanup --environment production

# Manual cleanup
aws cloudformation delete-stack --stack-name flight-cargo-assessment-production
```

### Resource Cleanup Checklist
- [ ] Delete CloudFormation stack
- [ ] Remove S3 buckets and objects
- [ ] Delete Lambda functions
- [ ] Remove IAM roles and policies
- [ ] Delete CloudWatch log groups
- [ ] Remove Bedrock agents

## Support and Maintenance

### Regular Maintenance Tasks
- Update dependencies monthly
- Review and update agent instructions
- Monitor performance metrics
- Update security configurations
- Test disaster recovery procedures

### Version Management
- Tag releases in version control
- Maintain deployment documentation
- Track configuration changes
- Plan upgrade procedures

### Getting Help
- AWS Support for infrastructure issues
- Bedrock documentation for agent configuration
- CloudFormation documentation for stack management
- Lambda documentation for function optimization

## Conclusion

This deployment guide provides comprehensive instructions for deploying the Flight Cargo Assessment System to Bedrock AgentCore. The automated deployment script handles most of the complexity, while the manual options provide flexibility for custom configurations.

For production deployments, ensure proper monitoring, security, and backup procedures are in place. Regular testing and maintenance will ensure optimal performance and reliability.

## Next Steps

After successful deployment:
1. Set up monitoring dashboards
2. Configure alerting and notifications
3. Implement CI/CD pipeline for updates
4. Plan for capacity scaling
5. Document operational procedures
6. Train operations team on maintenance procedures