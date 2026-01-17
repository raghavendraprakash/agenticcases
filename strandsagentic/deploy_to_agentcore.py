#!/usr/bin/env python3
"""
Complete deployment script for Flight Cargo Assessment to Bedrock AgentCore
"""

import os
import sys
import json
import boto3
import zipfile
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AgentCoreDeployment:
    """
    Complete deployment orchestrator for Bedrock AgentCore
    """
    
    def __init__(self, region: str = "us-east-1", environment: str = "production"):
        """
        Initialize deployment
        
        Args:
            region: AWS region
            environment: Deployment environment
        """
        self.region = region
        self.environment = environment
        self.stack_name = f"flight-cargo-assessment-{environment}"
        
        # AWS clients
        self.cloudformation = boto3.client('cloudformation', region_name=region)
        self.s3 = boto3.client('s3', region_name=region)
        self.lambda_client = boto3.client('lambda', region_name=region)
        self.bedrock_agent = boto3.client('bedrock-agent', region_name=region)
        
        # Deployment configuration
        self.config = {
            "agent_name": "flight-cargo-assessment-agent",
            "foundation_model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
            "lambda_runtime": "python3.11",
            "timeout": 300,
            "memory_size": 512
        }
    
    def validate_prerequisites(self) -> bool:
        """
        Validate deployment prerequisites
        
        Returns:
            True if all prerequisites are met
        """
        logger.info("🔍 Validating deployment prerequisites...")
        
        try:
            # Check AWS credentials
            sts = boto3.client('sts')
            identity = sts.get_caller_identity()
            logger.info(f"✅ AWS credentials valid for account: {identity['Account']}")
            
            # Check Bedrock access
            bedrock = boto3.client('bedrock', region_name=self.region)
            models = bedrock.list_foundation_models()
            claude_models = [m for m in models['modelSummaries'] if 'claude' in m['modelId'].lower()]
            logger.info(f"✅ Bedrock accessible with {len(claude_models)} Claude models")
            
            # Check required files
            required_files = [
                'lambda_handler.py',
                'bedrock_agentcore_cloudformation.yaml',
                'requirements.txt',
                'flight_cargo_assessment/'
            ]
            
            for file_path in required_files:
                if not Path(file_path).exists():
                    logger.error(f"❌ Required file/directory not found: {file_path}")
                    return False
            
            logger.info("✅ All required files present")
            
            # Check Python dependencies
            try:
                import boto3
                import click
                import rich
                logger.info("✅ Required Python packages available")
            except ImportError as e:
                logger.error(f"❌ Missing Python package: {e}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Prerequisites validation failed: {e}")
            return False
    
    def package_dependencies(self) -> str:
        """
        Package Python dependencies for Lambda layer
        
        Returns:
            Path to dependencies package
        """
        logger.info("📦 Packaging Python dependencies...")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            layer_dir = Path(temp_dir) / "python"
            layer_dir.mkdir()
            
            # Install dependencies
            subprocess.run([
                sys.executable, "-m", "pip", "install",
                "-r", "requirements.txt",
                "-t", str(layer_dir),
                "--no-deps"  # Only install what's in requirements.txt
            ], check=True)
            
            # Create zip file
            layer_zip = Path("dependencies_layer.zip")
            with zipfile.ZipFile(layer_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in layer_dir.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(temp_dir)
                        zipf.write(file_path, arcname)
            
            logger.info(f"✅ Dependencies packaged: {layer_zip}")
            return str(layer_zip)
    
    def package_application_code(self) -> str:
        """
        Package application code for Lambda
        
        Returns:
            Path to application package
        """
        logger.info("📦 Packaging application code...")
        
        app_zip = Path("agent_application.zip")
        
        with zipfile.ZipFile(app_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add Lambda handler
            zipf.write('lambda_handler.py')
            
            # Add flight_cargo_assessment package
            for py_file in Path('flight_cargo_assessment').rglob('*.py'):
                zipf.write(py_file)
            
            # Add configuration files
            if Path('bedrock_agent_config.json').exists():
                zipf.write('bedrock_agent_config.json')
        
        logger.info(f"✅ Application code packaged: {app_zip}")
        return str(app_zip)
    
    def upload_artifacts(self, bucket_name: str, dependencies_zip: str, app_zip: str) -> Dict[str, str]:
        """
        Upload deployment artifacts to S3
        
        Args:
            bucket_name: S3 bucket name
            dependencies_zip: Path to dependencies package
            app_zip: Path to application package
            
        Returns:
            Dictionary of S3 keys
        """
        logger.info(f"📤 Uploading artifacts to S3 bucket: {bucket_name}")
        
        artifacts = {}
        
        # Upload dependencies layer
        deps_key = f"layers/dependencies-{int(time.time())}.zip"
        self.s3.upload_file(dependencies_zip, bucket_name, deps_key)
        artifacts['dependencies'] = deps_key
        logger.info(f"✅ Uploaded dependencies: s3://{bucket_name}/{deps_key}")
        
        # Upload application code
        app_key = f"code/agent-code-{int(time.time())}.zip"
        self.s3.upload_file(app_zip, bucket_name, app_key)
        artifacts['application'] = app_key
        logger.info(f"✅ Uploaded application: s3://{bucket_name}/{app_key}")
        
        return artifacts
    
    def deploy_infrastructure(self) -> Dict[str, str]:
        """
        Deploy CloudFormation infrastructure
        
        Returns:
            Stack outputs
        """
        logger.info("🏗️ Deploying CloudFormation infrastructure...")
        
        # Read CloudFormation template
        with open('bedrock_agentcore_cloudformation.yaml', 'r') as f:
            template_body = f.read()
        
        parameters = [
            {
                'ParameterKey': 'AgentName',
                'ParameterValue': self.config['agent_name']
            },
            {
                'ParameterKey': 'Environment',
                'ParameterValue': self.environment
            },
            {
                'ParameterKey': 'FoundationModel',
                'ParameterValue': self.config['foundation_model']
            },
            {
                'ParameterKey': 'LambdaRuntime',
                'ParameterValue': self.config['lambda_runtime']
            }
        ]
        
        try:
            # Check if stack exists
            try:
                self.cloudformation.describe_stacks(StackName=self.stack_name)
                stack_exists = True
            except self.cloudformation.exceptions.ClientError:
                stack_exists = False
            
            if stack_exists:
                logger.info(f"📝 Updating existing stack: {self.stack_name}")
                self.cloudformation.update_stack(
                    StackName=self.stack_name,
                    TemplateBody=template_body,
                    Parameters=parameters,
                    Capabilities=['CAPABILITY_NAMED_IAM']
                )
                waiter = self.cloudformation.get_waiter('stack_update_complete')
            else:
                logger.info(f"🆕 Creating new stack: {self.stack_name}")
                self.cloudformation.create_stack(
                    StackName=self.stack_name,
                    TemplateBody=template_body,
                    Parameters=parameters,
                    Capabilities=['CAPABILITY_NAMED_IAM'],
                    Tags=[
                        {'Key': 'Project', 'Value': 'FlightCargoAssessment'},
                        {'Key': 'Environment', 'Value': self.environment},
                        {'Key': 'ManagedBy', 'Value': 'CloudFormation'}
                    ]
                )
                waiter = self.cloudformation.get_waiter('stack_create_complete')
            
            # Wait for completion
            logger.info("⏳ Waiting for stack deployment to complete...")
            waiter.wait(StackName=self.stack_name, WaiterConfig={'Delay': 30, 'MaxAttempts': 60})
            
            # Get stack outputs
            response = self.cloudformation.describe_stacks(StackName=self.stack_name)
            outputs = {}
            for output in response['Stacks'][0].get('Outputs', []):
                outputs[output['OutputKey']] = output['OutputValue']
            
            logger.info("✅ Infrastructure deployment completed")
            return outputs
            
        except Exception as e:
            logger.error(f"❌ Infrastructure deployment failed: {e}")
            raise
    
    def update_lambda_code(self, function_name: str, app_zip: str) -> None:
        """
        Update Lambda function code
        
        Args:
            function_name: Lambda function name
            app_zip: Path to application zip
        """
        logger.info(f"🔄 Updating Lambda function code: {function_name}")
        
        try:
            with open(app_zip, 'rb') as f:
                zip_content = f.read()
            
            self.lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=zip_content
            )
            
            # Wait for update to complete
            waiter = self.lambda_client.get_waiter('function_updated')
            waiter.wait(FunctionName=function_name)
            
            logger.info("✅ Lambda function code updated")
            
        except Exception as e:
            logger.error(f"❌ Lambda code update failed: {e}")
            raise
    
    def test_deployment(self, agent_id: str, agent_alias_id: str) -> bool:
        """
        Test the deployed agent
        
        Args:
            agent_id: Bedrock agent ID
            agent_alias_id: Agent alias ID
            
        Returns:
            True if tests pass
        """
        logger.info("🧪 Testing deployed agent...")
        
        try:
            # Test cargo assessment
            test_request = {
                "cargo_id": "DEPLOY_TEST_001",
                "dimensions": {
                    "length": 2.0,
                    "width": 1.5,
                    "height": 1.2
                },
                "weight": 800,
                "stackable": True,
                "tiltable": False,
                "fragile": False,
                "cargo_type": "electronics",
                "preferred_deck": "lower_deck",
                "priority": "high"
            }
            
            # Invoke agent
            bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name=self.region)
            
            response = bedrock_agent_runtime.invoke_agent(
                agentId=agent_id,
                agentAliasId=agent_alias_id,
                sessionId=f"test-session-{int(time.time())}",
                inputText=f"Please assess this cargo: {json.dumps(test_request)}"
            )
            
            # Process response
            response_text = ""
            for event in response['completion']:
                if 'chunk' in event:
                    response_text += event['chunk']['bytes'].decode('utf-8')
            
            if response_text and "assessment_successful" in response_text:
                logger.info("✅ Agent test successful")
                return True
            else:
                logger.warning("⚠️ Agent test returned unexpected response")
                return False
                
        except Exception as e:
            logger.error(f"❌ Agent test failed: {e}")
            return False
    
    def deploy(self) -> Dict[str, Any]:
        """
        Execute complete deployment
        
        Returns:
            Deployment information
        """
        logger.info("🚀 Starting Bedrock AgentCore deployment...")
        logger.info("=" * 60)
        
        try:
            # Step 1: Validate prerequisites
            if not self.validate_prerequisites():
                raise Exception("Prerequisites validation failed")
            
            # Step 2: Package code
            dependencies_zip = self.package_dependencies()
            app_zip = self.package_application_code()
            
            # Step 3: Deploy infrastructure
            outputs = self.deploy_infrastructure()
            
            # Step 4: Upload artifacts
            bucket_name = outputs.get('S3BucketName')
            if bucket_name:
                artifacts = self.upload_artifacts(bucket_name, dependencies_zip, app_zip)
                
                # Step 5: Update Lambda code
                lambda_arn = outputs.get('LambdaFunctionArn')
                if lambda_arn:
                    function_name = lambda_arn.split(':')[-1]
                    self.update_lambda_code(function_name, app_zip)
            
            # Step 6: Test deployment
            agent_id = outputs.get('AgentId')
            agent_alias_id = outputs.get('AgentAliasId')
            
            if agent_id and agent_alias_id:
                test_passed = self.test_deployment(agent_id, agent_alias_id)
            else:
                test_passed = False
                logger.warning("⚠️ Agent IDs not available, skipping tests")
            
            # Prepare deployment info
            deployment_info = {
                "status": "success",
                "environment": self.environment,
                "region": self.region,
                "stack_name": self.stack_name,
                "agent_id": agent_id,
                "agent_alias_id": agent_alias_id,
                "lambda_function_arn": outputs.get('LambdaFunctionArn'),
                "s3_bucket": bucket_name,
                "agent_role_arn": outputs.get('AgentRoleArn'),
                "test_passed": test_passed,
                "deployment_time": time.time()
            }
            
            # Clean up temporary files
            for temp_file in [dependencies_zip, app_zip]:
                if Path(temp_file).exists():
                    Path(temp_file).unlink()
            
            logger.info("\n" + "=" * 60)
            logger.info("🎉 Deployment Complete!")
            logger.info("=" * 60)
            logger.info(f"Environment: {self.environment}")
            logger.info(f"Region: {self.region}")
            logger.info(f"Agent ID: {agent_id}")
            logger.info(f"Agent Alias ID: {agent_alias_id}")
            logger.info(f"Test Status: {'✅ PASSED' if test_passed else '❌ FAILED'}")
            
            return deployment_info
            
        except Exception as e:
            logger.error(f"\n❌ Deployment failed: {e}")
            raise
    
    def cleanup(self) -> None:
        """Clean up deployment resources"""
        logger.info("🧹 Cleaning up deployment resources...")
        
        try:
            # Delete CloudFormation stack
            self.cloudformation.delete_stack(StackName=self.stack_name)
            
            # Wait for deletion
            waiter = self.cloudformation.get_waiter('stack_delete_complete')
            waiter.wait(StackName=self.stack_name)
            
            logger.info("✅ Cleanup completed")
            
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")
            raise


def main():
    """Main deployment function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Deploy Flight Cargo Assessment to Bedrock AgentCore")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--environment", default="production", choices=["development", "staging", "production"], help="Environment")
    parser.add_argument("--cleanup", action="store_true", help="Clean up deployment")
    parser.add_argument("--validate-only", action="store_true", help="Only validate prerequisites")
    
    args = parser.parse_args()
    
    # Create deployer
    deployer = AgentCoreDeployment(region=args.region, environment=args.environment)
    
    try:
        if args.cleanup:
            deployer.cleanup()
        elif args.validate_only:
            if deployer.validate_prerequisites():
                logger.info("✅ All prerequisites validated successfully")
            else:
                logger.error("❌ Prerequisites validation failed")
                sys.exit(1)
        else:
            # Full deployment
            deployment_info = deployer.deploy()
            
            # Save deployment info
            info_file = f"deployment_info_{args.environment}.json"
            with open(info_file, 'w') as f:
                json.dump(deployment_info, f, indent=2, default=str)
            
            logger.info(f"\n📄 Deployment info saved to: {info_file}")
            
            # Print next steps
            logger.info("\n📋 Next Steps:")
            logger.info("1. Test the agent using AWS Console or SDK")
            logger.info("2. Configure monitoring and alerting")
            logger.info("3. Set up CI/CD pipeline for updates")
            logger.info("4. Configure custom domain if needed")
            logger.info("5. Set up backup and disaster recovery")
            
    except KeyboardInterrupt:
        logger.info("\n⏹️ Deployment interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n💥 Deployment failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()