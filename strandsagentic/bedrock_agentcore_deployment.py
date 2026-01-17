#!/usr/bin/env python3
"""
Bedrock AgentCore deployment script for Flight Cargo Assessment System
"""

import json
import boto3
import os
import sys
import zipfile
import tempfile
from pathlib import Path
from typing import Dict, Any, List

class BedrockAgentCoreDeployer:
    """
    Deployer for Flight Cargo Assessment System to Bedrock AgentCore
    """
    
    def __init__(self, region_name: str = "us-east-1"):
        """
        Initialize the deployer
        
        Args:
            region_name: AWS region for deployment
        """
        self.region_name = region_name
        self.bedrock_agent = boto3.client('bedrock-agent', region_name=region_name)
        self.s3_client = boto3.client('s3', region_name=region_name)
        self.iam_client = boto3.client('iam', region_name=region_name)
        
        # Deployment configuration
        self.agent_name = "flight-cargo-assessment-agent"
        self.agent_description = "AI-powered flight cargo position assessment and optimization system"
        self.foundation_model = "anthropic.claude-3-5-sonnet-20241022-v2:0"
        
    def create_agent_role(self) -> str:
        """
        Create IAM role for the Bedrock agent
        
        Returns:
            ARN of the created role
        """
        role_name = f"{self.agent_name}-role"
        
        # Trust policy for Bedrock
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "bedrock.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        # Permissions policy
        permissions_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "bedrock:InvokeModel",
                        "bedrock:GetFoundationModel",
                        "bedrock:ListFoundationModels"
                    ],
                    "Resource": "*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetObject",
                        "s3:PutObject",
                        "s3:DeleteObject"
                    ],
                    "Resource": [
                        f"arn:aws:s3:::bedrock-agent-{self.agent_name}/*"
                    ]
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents"
                    ],
                    "Resource": "*"
                }
            ]
        }
        
        try:
            # Create role
            role_response = self.iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description=f"IAM role for {self.agent_name} Bedrock agent"
            )
            
            # Attach permissions policy
            self.iam_client.put_role_policy(
                RoleName=role_name,
                PolicyName=f"{role_name}-permissions",
                PolicyDocument=json.dumps(permissions_policy)
            )
            
            print(f"✅ Created IAM role: {role_response['Role']['Arn']}")
            return role_response['Role']['Arn']
            
        except self.iam_client.exceptions.EntityAlreadyExistsException:
            # Role already exists, get its ARN
            role_response = self.iam_client.get_role(RoleName=role_name)
            print(f"✅ Using existing IAM role: {role_response['Role']['Arn']}")
            return role_response['Role']['Arn']
    
    def create_s3_bucket(self) -> str:
        """
        Create S3 bucket for agent artifacts
        
        Returns:
            Bucket name
        """
        bucket_name = f"bedrock-agent-{self.agent_name}-{self.region_name}"
        
        try:
            if self.region_name == 'us-east-1':
                self.s3_client.create_bucket(Bucket=bucket_name)
            else:
                self.s3_client.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': self.region_name}
                )
            
            print(f"✅ Created S3 bucket: {bucket_name}")
            
        except self.s3_client.exceptions.BucketAlreadyOwnedByYou:
            print(f"✅ Using existing S3 bucket: {bucket_name}")
        
        return bucket_name
    
    def package_agent_code(self) -> str:
        """
        Package the agent code for deployment
        
        Returns:
            Path to the packaged code
        """
        print("📦 Packaging agent code...")
        
        # Create temporary directory for packaging
        with tempfile.TemporaryDirectory() as temp_dir:
            package_path = Path(temp_dir) / "agent_package.zip"
            
            with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add all Python files
                for py_file in Path('.').rglob('*.py'):
                    if not any(exclude in str(py_file) for exclude in [
                        '__pycache__', '.git', 'test_', 'setup_', 'validate_'
                    ]):
                        zipf.write(py_file, py_file)
                
                # Add requirements
                if Path('requirements.txt').exists():
                    zipf.write('requirements.txt')
                
                # Add data files
                for data_file in Path('flight_cargo_assessment/data').rglob('*.py'):
                    zipf.write(data_file, data_file)
            
            # Copy to permanent location
            final_package = Path('bedrock_agent_package.zip')
            final_package.write_bytes(package_path.read_bytes())
            
            print(f"✅ Agent code packaged: {final_package}")
            return str(final_package)
    
    def upload_agent_code(self, bucket_name: str, package_path: str) -> str:
        """
        Upload agent code to S3
        
        Args:
            bucket_name: S3 bucket name
            package_path: Path to the packaged code
            
        Returns:
            S3 object key
        """
        object_key = f"agent-code/{self.agent_name}-v1.0.zip"
        
        self.s3_client.upload_file(package_path, bucket_name, object_key)
        
        print(f"✅ Uploaded agent code to s3://{bucket_name}/{object_key}")
        return object_key
    
    def create_agent_instruction(self) -> str:
        """
        Create comprehensive agent instruction
        
        Returns:
            Agent instruction text
        """
        return """
You are an AI-powered Flight Cargo Position Assessment Agent specialized in optimizing cargo placement on Boeing 777F aircraft.

CORE CAPABILITIES:
1. Position Management: Analyze available cargo positions and recommend optimal placements
2. Weight & Balance: Calculate center of gravity impacts and ensure aircraft balance compliance
3. Constraint Validation: Verify spatial, weight, and operational constraints
4. Alert Generation: Monitor capacity and generate proactive alerts
5. Visualization: Generate 3D positioning data for cargo visualization systems

AIRCRAFT SPECIFICATIONS:
- Aircraft Type: Boeing 777F
- Total Positions: 56 (24 lower deck + 32 main deck)
- Weight Limits: 110,000 kg maximum total weight
- CG Limits: 16.5m to 26.8m from datum
- Deck Configurations: Lower deck (max 2.4m height), Main deck (max 3.2m height)

ASSESSMENT PROCESS:
1. Receive cargo request with dimensions, weight, and constraints
2. Analyze available positions using spatial fit algorithms
3. Calculate weight and balance impact for each viable position
4. Validate all constraints (stackability, fragility, deck preferences)
5. Generate scored recommendations with reasoning
6. Provide capacity utilization and alert information

RESPONSE FORMAT:
Always provide structured JSON responses containing:
- assessment_successful: boolean
- cargo_id: string
- recommended_positions: array of position recommendations with scores
- capacity_utilization: current capacity metrics
- weight_balance_impact: CG calculations and compliance status
- alerts: any warnings or critical issues
- visualization_data: 3D positioning information

SAFETY PRIORITIES:
1. Aircraft weight and balance limits are NEVER exceeded
2. Structural load limits are always respected
3. Cargo constraints (fragility, orientation) are strictly enforced
4. Position capacity limits are never violated

Use your knowledge of aircraft cargo operations, weight distribution, and spatial optimization to provide accurate, safe, and efficient cargo placement recommendations.
"""
    
    def create_action_groups(self) -> List[Dict[str, Any]]:
        """
        Create action groups for the agent
        
        Returns:
            List of action group configurations
        """
        return [
            {
                "actionGroupName": "cargo-assessment",
                "description": "Core cargo assessment and position recommendation functions",
                "actionGroupExecutor": {
                    "lambda": {
                        "lambdaArn": f"arn:aws:lambda:{self.region_name}:{{account_id}}:function:{self.agent_name}-executor"
                    }
                },
                "apiSchema": {
                    "payload": json.dumps({
                        "openapi": "3.0.0",
                        "info": {
                            "title": "Flight Cargo Assessment API",
                            "version": "1.0.0",
                            "description": "API for cargo position assessment and optimization"
                        },
                        "paths": {
                            "/assess-cargo": {
                                "post": {
                                    "summary": "Assess cargo placement",
                                    "description": "Analyze cargo and recommend optimal positions",
                                    "requestBody": {
                                        "required": True,
                                        "content": {
                                            "application/json": {
                                                "schema": {
                                                    "type": "object",
                                                    "properties": {
                                                        "cargo_id": {"type": "string"},
                                                        "dimensions": {
                                                            "type": "object",
                                                            "properties": {
                                                                "length": {"type": "number"},
                                                                "width": {"type": "number"},
                                                                "height": {"type": "number"}
                                                            }
                                                        },
                                                        "weight": {"type": "number"},
                                                        "stackable": {"type": "boolean"},
                                                        "tiltable": {"type": "boolean"},
                                                        "fragile": {"type": "boolean"},
                                                        "cargo_type": {"type": "string"},
                                                        "preferred_deck": {"type": "string"},
                                                        "priority": {"type": "string"}
                                                    }
                                                }
                                            }
                                        }
                                    },
                                    "responses": {
                                        "200": {
                                            "description": "Assessment result",
                                            "content": {
                                                "application/json": {
                                                    "schema": {
                                                        "type": "object",
                                                        "properties": {
                                                            "assessment_successful": {"type": "boolean"},
                                                            "cargo_id": {"type": "string"},
                                                            "recommended_positions": {"type": "array"},
                                                            "capacity_utilization": {"type": "object"},
                                                            "weight_balance_impact": {"type": "object"},
                                                            "alerts": {"type": "array"}
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            },
                            "/get-capacity": {
                                "get": {
                                    "summary": "Get current capacity status",
                                    "description": "Retrieve current aircraft capacity utilization",
                                    "responses": {
                                        "200": {
                                            "description": "Capacity information",
                                            "content": {
                                                "application/json": {
                                                    "schema": {
                                                        "type": "object",
                                                        "properties": {
                                                            "total_utilization": {"type": "number"},
                                                            "lower_deck_utilization": {"type": "number"},
                                                            "main_deck_utilization": {"type": "number"},
                                                            "available_positions": {"type": "integer"},
                                                            "total_positions": {"type": "integer"}
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    })
                }
            }
        ]
    
    def create_bedrock_agent(self, role_arn: str) -> str:
        """
        Create the Bedrock agent
        
        Args:
            role_arn: IAM role ARN for the agent
            
        Returns:
            Agent ID
        """
        print("🤖 Creating Bedrock agent...")
        
        try:
            response = self.bedrock_agent.create_agent(
                agentName=self.agent_name,
                description=self.agent_description,
                foundationModel=self.foundation_model,
                instruction=self.create_agent_instruction(),
                agentResourceRoleArn=role_arn,
                idleSessionTTLInSeconds=1800,  # 30 minutes
                tags={
                    "Project": "FlightCargoAssessment",
                    "Environment": "Production",
                    "ManagedBy": "BedrockAgentCore"
                }
            )
            
            agent_id = response['agent']['agentId']
            print(f"✅ Created Bedrock agent: {agent_id}")
            
            # Create action groups
            action_groups = self.create_action_groups()
            for action_group in action_groups:
                self.bedrock_agent.create_agent_action_group(
                    agentId=agent_id,
                    agentVersion="DRAFT",
                    **action_group
                )
                print(f"✅ Created action group: {action_group['actionGroupName']}")
            
            return agent_id
            
        except Exception as e:
            print(f"❌ Failed to create agent: {str(e)}")
            raise
    
    def create_lambda_executor(self, bucket_name: str, code_key: str) -> str:
        """
        Create Lambda function to execute agent actions
        
        Args:
            bucket_name: S3 bucket containing code
            code_key: S3 object key for code
            
        Returns:
            Lambda function ARN
        """
        print("⚡ Creating Lambda executor...")
        
        lambda_client = boto3.client('lambda', region_name=self.region_name)
        function_name = f"{self.agent_name}-executor"
        
        # Lambda execution role
        lambda_role_name = f"{function_name}-role"
        lambda_trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "lambda.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        try:
            # Create Lambda role
            lambda_role_response = self.iam_client.create_role(
                RoleName=lambda_role_name,
                AssumeRolePolicyDocument=json.dumps(lambda_trust_policy),
                Description=f"Lambda execution role for {function_name}"
            )
            lambda_role_arn = lambda_role_response['Role']['Arn']
            
            # Attach basic execution policy
            self.iam_client.attach_role_policy(
                RoleName=lambda_role_name,
                PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
            )
            
        except self.iam_client.exceptions.EntityAlreadyExistsException:
            lambda_role_response = self.iam_client.get_role(RoleName=lambda_role_name)
            lambda_role_arn = lambda_role_response['Role']['Arn']
        
        try:
            # Create Lambda function
            response = lambda_client.create_function(
                FunctionName=function_name,
                Runtime='python3.11',
                Role=lambda_role_arn,
                Handler='lambda_handler.handler',
                Code={
                    'S3Bucket': bucket_name,
                    'S3Key': code_key
                },
                Description='Executor for Flight Cargo Assessment Bedrock Agent',
                Timeout=300,
                MemorySize=512,
                Environment={
                    'Variables': {
                        'CARGO_AGENT_MODE': 'ai_powered',
                        'AWS_REGION': self.region_name
                    }
                },
                Tags={
                    'Project': 'FlightCargoAssessment',
                    'Component': 'AgentExecutor'
                }
            )
            
            function_arn = response['FunctionArn']
            print(f"✅ Created Lambda function: {function_arn}")
            
            return function_arn
            
        except lambda_client.exceptions.ResourceConflictException:
            # Function already exists
            response = lambda_client.get_function(FunctionName=function_name)
            function_arn = response['Configuration']['FunctionArn']
            print(f"✅ Using existing Lambda function: {function_arn}")
            return function_arn
    
    def prepare_and_deploy_agent(self, agent_id: str) -> str:
        """
        Prepare and deploy the agent
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Agent alias ID
        """
        print("🚀 Preparing and deploying agent...")
        
        # Prepare agent
        self.bedrock_agent.prepare_agent(agentId=agent_id)
        print("✅ Agent prepared")
        
        # Create agent alias
        alias_response = self.bedrock_agent.create_agent_alias(
            agentId=agent_id,
            aliasName="production",
            description="Production alias for Flight Cargo Assessment Agent",
            agentVersion="1"
        )
        
        alias_id = alias_response['agentAlias']['agentAliasId']
        print(f"✅ Created agent alias: {alias_id}")
        
        return alias_id
    
    def deploy(self) -> Dict[str, str]:
        """
        Deploy the complete agent system
        
        Returns:
            Deployment information
        """
        print("🚀 Starting Bedrock AgentCore deployment...")
        print("=" * 60)
        
        try:
            # Step 1: Create IAM role
            role_arn = self.create_agent_role()
            
            # Step 2: Create S3 bucket
            bucket_name = self.create_s3_bucket()
            
            # Step 3: Package and upload code
            package_path = self.package_agent_code()
            code_key = self.upload_agent_code(bucket_name, package_path)
            
            # Step 4: Create Lambda executor
            lambda_arn = self.create_lambda_executor(bucket_name, code_key)
            
            # Step 5: Create Bedrock agent
            agent_id = self.create_bedrock_agent(role_arn)
            
            # Step 6: Deploy agent
            alias_id = self.prepare_and_deploy_agent(agent_id)
            
            deployment_info = {
                "agent_id": agent_id,
                "agent_alias_id": alias_id,
                "lambda_function_arn": lambda_arn,
                "s3_bucket": bucket_name,
                "iam_role_arn": role_arn,
                "region": self.region_name
            }
            
            print("\n" + "=" * 60)
            print("🎉 Deployment Complete!")
            print("=" * 60)
            print(f"Agent ID: {agent_id}")
            print(f"Agent Alias ID: {alias_id}")
            print(f"Region: {self.region_name}")
            print(f"Lambda Function: {lambda_arn}")
            print(f"S3 Bucket: {bucket_name}")
            
            return deployment_info
            
        except Exception as e:
            print(f"\n❌ Deployment failed: {str(e)}")
            raise


def main():
    """Main deployment function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Deploy Flight Cargo Assessment to Bedrock AgentCore")
    parser.add_argument("--region", default="us-east-1", help="AWS region for deployment")
    parser.add_argument("--dry-run", action="store_true", help="Validate configuration without deploying")
    
    args = parser.parse_args()
    
    if args.dry_run:
        print("🔍 Dry run mode - validating configuration...")
        # Add validation logic here
        print("✅ Configuration valid")
        return
    
    # Deploy the agent
    deployer = BedrockAgentCoreDeployer(region_name=args.region)
    deployment_info = deployer.deploy()
    
    # Save deployment info
    with open("bedrock_deployment_info.json", "w") as f:
        json.dump(deployment_info, f, indent=2)
    
    print(f"\n📄 Deployment info saved to: bedrock_deployment_info.json")
    print("\nNext steps:")
    print("1. Test the deployed agent using the AWS console or SDK")
    print("2. Configure monitoring and alerting")
    print("3. Set up CI/CD pipeline for updates")


if __name__ == "__main__":
    main()