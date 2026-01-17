#!/usr/bin/env python3
"""
Bedrock setup validation script
"""

import os
import sys
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flight_cargo_assessment.bedrock.config import BedrockConfig


def check_aws_credentials():
    """Check AWS credentials configuration"""
    print("🔐 Checking AWS Credentials...")
    
    try:
        session = boto3.Session()
        credentials = session.get_credentials()
        
        if not credentials:
            print("❌ No AWS credentials found")
            print("   Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables")
            print("   Or configure AWS CLI with 'aws configure'")
            return False
        
        print("✅ AWS credentials found")
        
        # Test credentials by listing regions
        ec2 = boto3.client('ec2', region_name='us-east-1')
        regions = ec2.describe_regions()
        print(f"   Available regions: {len(regions['Regions'])}")
        
        return True
        
    except NoCredentialsError:
        print("❌ AWS credentials not configured")
        return False
    except ClientError as e:
        print(f"❌ AWS credentials invalid: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Error checking credentials: {str(e)}")
        return False


def check_bedrock_access():
    """Check Bedrock service access"""
    print("\n🧠 Checking Bedrock Access...")
    
    try:
        region = os.getenv("AWS_REGION", "us-east-1")
        bedrock = boto3.client('bedrock', region_name=region)
        
        # List foundation models
        models = bedrock.list_foundation_models()
        
        claude_models = [
            model for model in models['modelSummaries'] 
            if 'claude' in model['modelId'].lower()
        ]
        
        print(f"✅ Bedrock accessible in {region}")
        print(f"   Claude models available: {len(claude_models)}")
        
        # Check specific models we need
        required_models = [
            "anthropic.claude-3-5-sonnet-20241022-v2:0",
            "anthropic.claude-3-5-haiku-20241022-v1:0"
        ]
        
        available_model_ids = [model['modelId'] for model in models['modelSummaries']]
        
        for model_id in required_models:
            if model_id in available_model_ids:
                print(f"   ✅ {model_id}")
            else:
                print(f"   ❌ {model_id} (not available)")
        
        return len(claude_models) > 0
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'UnauthorizedOperation':
            print("❌ No permission to access Bedrock")
            print("   Ensure your AWS user/role has bedrock:* permissions")
        else:
            print(f"❌ Bedrock access error: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Error checking Bedrock: {str(e)}")
        return False


def check_bedrock_runtime():
    """Check Bedrock Runtime access"""
    print("\n⚡ Checking Bedrock Runtime...")
    
    try:
        region = os.getenv("AWS_REGION", "us-east-1")
        bedrock_runtime = boto3.client('bedrock-runtime', region_name=region)
        
        # Try a simple invocation with Haiku (cheapest)
        model_id = "anthropic.claude-3-5-haiku-20241022-v1:0"
        
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 10,
            "temperature": 0.1,
            "messages": [{"role": "user", "content": "Hello"}]
        }
        
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            body=str(body).encode(),
            contentType="application/json",
            accept="application/json"
        )
        
        print("✅ Bedrock Runtime accessible")
        print("   Successfully invoked Claude Haiku")
        
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'AccessDeniedException':
            print("❌ No permission to invoke Bedrock models")
            print("   Ensure your AWS user/role has bedrock:InvokeModel permission")
        elif error_code == 'ValidationException':
            print("❌ Model not available or request format invalid")
        else:
            print(f"❌ Bedrock Runtime error: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Error checking Bedrock Runtime: {str(e)}")
        return False


def check_configuration():
    """Check Bedrock configuration"""
    print("\n⚙️  Checking Configuration...")
    
    try:
        config = BedrockConfig.create_default_config()
        validation = config.validate_configuration()
        
        if validation['valid']:
            print("✅ Configuration valid")
        else:
            print("❌ Configuration issues:")
            for issue in validation['issues']:
                print(f"   - {issue}")
        
        if validation['warnings']:
            print("⚠️  Configuration warnings:")
            for warning in validation['warnings']:
                print(f"   - {warning}")
        
        # Show configuration details
        print(f"\nConfiguration Details:")
        print(f"   Region: {config.region_name}")
        print(f"   Models: {list(config.model_config.keys())}")
        print(f"   Agents: {list(config.agent_config.keys())}")
        
        return validation['valid']
        
    except Exception as e:
        print(f"❌ Configuration error: {str(e)}")
        return False


def check_environment():
    """Check environment variables"""
    print("\n🌍 Checking Environment Variables...")
    
    env_vars = {
        "AWS_REGION": os.getenv("AWS_REGION", "us-east-1"),
        "AWS_ACCESS_KEY_ID": "***" if os.getenv("AWS_ACCESS_KEY_ID") else "Not set",
        "AWS_SECRET_ACCESS_KEY": "***" if os.getenv("AWS_SECRET_ACCESS_KEY") else "Not set",
        "CARGO_AGENT_MODE": os.getenv("CARGO_AGENT_MODE", "rule_based")
    }
    
    for var, value in env_vars.items():
        print(f"   {var}: {value}")
    
    # Check required variables for AI mode
    agent_mode = env_vars["CARGO_AGENT_MODE"]
    if agent_mode in ["ai_powered", "hybrid"]:
        if env_vars["AWS_ACCESS_KEY_ID"] == "Not set":
            print("⚠️  AWS_ACCESS_KEY_ID not set (required for AI mode)")
            return False
        if env_vars["AWS_SECRET_ACCESS_KEY"] == "Not set":
            print("⚠️  AWS_SECRET_ACCESS_KEY not set (required for AI mode)")
            return False
    
    print("✅ Environment variables configured")
    return True


def check_dependencies():
    """Check Python dependencies"""
    print("\n📦 Checking Dependencies...")
    
    required_packages = [
        "boto3",
        "botocore",
        "click",
        "rich"
    ]
    
    missing = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package}")
            missing.append(package)
    
    if missing:
        print(f"\n❌ Missing packages: {', '.join(missing)}")
        print("   Install with: pip install " + " ".join(missing))
        return False
    
    print("✅ All dependencies installed")
    return True


def provide_setup_instructions():
    """Provide setup instructions"""
    print("\n" + "=" * 60)
    print("🛠️  SETUP INSTRUCTIONS")
    print("=" * 60)
    
    print("\n1. Install Dependencies:")
    print("   pip install boto3 botocore click rich")
    
    print("\n2. Configure AWS Credentials:")
    print("   Option A - Environment Variables:")
    print("     export AWS_ACCESS_KEY_ID=your_access_key")
    print("     export AWS_SECRET_ACCESS_KEY=your_secret_key")
    print("     export AWS_REGION=us-east-1")
    
    print("\n   Option B - AWS CLI:")
    print("     aws configure")
    
    print("\n3. Set Agent Mode:")
    print("     export CARGO_AGENT_MODE=hybrid  # or ai_powered")
    
    print("\n4. Ensure AWS Permissions:")
    print("   Your AWS user/role needs these permissions:")
    print("   - bedrock:ListFoundationModels")
    print("   - bedrock:InvokeModel")
    print("   - bedrock:GetFoundationModel")
    
    print("\n5. Test Setup:")
    print("   python validate_bedrock_setup.py")
    print("   python test_bedrock_integration.py")


def main():
    """Run all validation checks"""
    print("🔍 Bedrock Setup Validation")
    print("=" * 50)
    
    checks = [
        ("Dependencies", check_dependencies),
        ("Environment Variables", check_environment),
        ("AWS Credentials", check_aws_credentials),
        ("Bedrock Access", check_bedrock_access),
        ("Bedrock Runtime", check_bedrock_runtime),
        ("Configuration", check_configuration)
    ]
    
    results = {}
    
    for check_name, check_func in checks:
        try:
            results[check_name] = check_func()
        except Exception as e:
            print(f"❌ {check_name} failed with exception: {str(e)}")
            results[check_name] = False
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Validation Summary")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for check_name, passed_check in results.items():
        status = "✅ PASS" if passed_check else "❌ FAIL"
        print(f"{check_name}: {status}")
        if passed_check:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} checks passed")
    
    if passed == total:
        print("🎉 Bedrock setup is complete and working!")
        print("\nYou can now use AI-powered agents:")
        print("  export CARGO_AGENT_MODE=ai_powered")
        print("  python -m flight_cargo_assessment.cli --test-ai")
        return 0
    else:
        print("⚠️  Setup incomplete. See instructions below.")
        provide_setup_instructions()
        return 1


if __name__ == "__main__":
    sys.exit(main())