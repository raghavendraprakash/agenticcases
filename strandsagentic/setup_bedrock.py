#!/usr/bin/env python3
"""
Interactive Bedrock setup script
"""

import os
import sys
import subprocess
from pathlib import Path


def print_header(title):
    """Print a formatted header"""
    print("\n" + "=" * 60)
    print(f"🚀 {title}")
    print("=" * 60)


def print_step(step_num, title):
    """Print a formatted step"""
    print(f"\n📋 Step {step_num}: {title}")
    print("-" * 40)


def check_python_version():
    """Check Python version"""
    print_step(1, "Checking Python Version")
    
    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8+ required")
        return False
    
    print("✅ Python version compatible")
    return True


def install_dependencies():
    """Install Python dependencies"""
    print_step(2, "Installing Dependencies")
    
    try:
        print("Installing required packages...")
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ], check=True)
        
        print("✅ Dependencies installed successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False
    except FileNotFoundError:
        print("❌ requirements.txt not found")
        return False


def setup_aws_credentials():
    """Guide user through AWS credentials setup"""
    print_step(3, "AWS Credentials Setup")
    
    # Check if credentials already exist
    if os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"):
        print("✅ AWS credentials found in environment variables")
        return True
    
    # Check AWS CLI configuration
    try:
        result = subprocess.run(["aws", "configure", "list"], 
                              capture_output=True, text=True)
        if result.returncode == 0 and "access_key" in result.stdout:
            print("✅ AWS credentials found in AWS CLI configuration")
            return True
    except FileNotFoundError:
        pass
    
    print("AWS credentials not found. You have several options:")
    print("\n1. Environment Variables (Recommended for development):")
    print("   export AWS_ACCESS_KEY_ID=your_access_key_here")
    print("   export AWS_SECRET_ACCESS_KEY=your_secret_key_here")
    print("   export AWS_REGION=us-east-1")
    
    print("\n2. AWS CLI Configuration:")
    print("   aws configure")
    
    print("\n3. IAM Roles (For EC2/Lambda deployment)")
    
    choice = input("\nChoose setup method (1/2/3) or 's' to skip: ").strip()
    
    if choice == "1":
        access_key = input("Enter AWS Access Key ID: ").strip()
        secret_key = input("Enter AWS Secret Access Key: ").strip()
        region = input("Enter AWS Region (default: us-east-1): ").strip() or "us-east-1"
        
        # Create .env file
        env_content = f"""# AWS Configuration
AWS_ACCESS_KEY_ID={access_key}
AWS_SECRET_ACCESS_KEY={secret_key}
AWS_REGION={region}

# Agent Configuration
CARGO_AGENT_MODE=hybrid
"""
        
        with open(".env", "w") as f:
            f.write(env_content)
        
        print("✅ Credentials saved to .env file")
        print("   Add 'source .env' to your shell profile or use python-dotenv")
        return True
        
    elif choice == "2":
        try:
            subprocess.run(["aws", "configure"], check=True)
            print("✅ AWS CLI configured")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ AWS CLI configuration failed")
            return False
    
    elif choice == "3":
        print("✅ Using IAM roles (ensure your environment has appropriate roles)")
        return True
    
    else:
        print("⚠️  Skipping AWS credentials setup")
        return False


def configure_agent_mode():
    """Configure agent mode"""
    print_step(4, "Agent Mode Configuration")
    
    current_mode = os.getenv("CARGO_AGENT_MODE", "rule_based")
    print(f"Current agent mode: {current_mode}")
    
    print("\nAvailable modes:")
    print("1. rule_based  - Traditional rule-based agents (no AWS costs)")
    print("2. hybrid      - AI agents with rule-based fallback (recommended)")
    print("3. ai_powered  - Full AI-powered agents (requires AWS setup)")
    
    choice = input(f"\nSelect mode (1/2/3) or press Enter for current [{current_mode}]: ").strip()
    
    mode_map = {
        "1": "rule_based",
        "2": "hybrid", 
        "3": "ai_powered"
    }
    
    if choice in mode_map:
        new_mode = mode_map[choice]
        
        # Update .env file
        env_file = Path(".env")
        if env_file.exists():
            content = env_file.read_text()
            if "CARGO_AGENT_MODE=" in content:
                # Replace existing
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if line.startswith("CARGO_AGENT_MODE="):
                        lines[i] = f"CARGO_AGENT_MODE={new_mode}"
                        break
                content = '\n'.join(lines)
            else:
                # Add new
                content += f"\nCARGO_AGENT_MODE={new_mode}\n"
            
            env_file.write_text(content)
        else:
            # Create new .env file
            env_file.write_text(f"CARGO_AGENT_MODE={new_mode}\n")
        
        print(f"✅ Agent mode set to: {new_mode}")
        return True
    
    print(f"✅ Keeping current mode: {current_mode}")
    return True


def test_setup():
    """Test the setup"""
    print_step(5, "Testing Setup")
    
    try:
        # Test basic imports
        print("Testing imports...")
        import boto3
        import click
        import rich
        print("✅ Core dependencies working")
        
        # Test configuration
        print("Testing configuration...")
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from flight_cargo_assessment.bedrock.config import BedrockConfig
        
        config = BedrockConfig.create_default_config()
        validation = config.validate_configuration()
        
        if validation['valid']:
            print("✅ Configuration valid")
        else:
            print("⚠️  Configuration issues found")
            for issue in validation['issues']:
                print(f"   - {issue}")
        
        # Test agent factory
        print("Testing agent factory...")
        from flight_cargo_assessment.agents.agent_factory import AgentFactory
        
        factory = AgentFactory.from_environment()
        info = factory.get_agent_info()
        print(f"✅ Agent factory working (mode: {info['mode']})")
        
        return True
        
    except Exception as e:
        print(f"❌ Setup test failed: {str(e)}")
        return False


def create_sample_files():
    """Create sample configuration files"""
    print_step(6, "Creating Sample Files")
    
    # Create sample environment file
    sample_env = """# Flight Cargo Assessment Configuration

# AWS Configuration
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_REGION=us-east-1

# Agent Configuration
CARGO_AGENT_MODE=hybrid

# Optional: Logging Configuration
LOG_LEVEL=INFO
"""
    
    with open(".env.sample", "w") as f:
        f.write(sample_env)
    
    print("✅ Created .env.sample")
    
    # Create quick start script
    quickstart = """#!/bin/bash
# Quick start script for Flight Cargo Assessment

echo "🚀 Flight Cargo Assessment Quick Start"
echo "======================================"

# Load environment variables
if [ -f .env ]; then
    source .env
    echo "✅ Loaded environment variables"
else
    echo "⚠️  No .env file found - using defaults"
fi

# Test the system
echo ""
echo "🔍 Testing system status..."
python -m flight_cargo_assessment.cli --status

echo ""
echo "🧪 Running basic test..."
python -m flight_cargo_assessment.cli \\
    --length 2.0 --width 1.5 --height 1.2 --weight 800 \\
    --stackable --type electronics --priority high

echo ""
echo "✅ Quick start complete!"
echo "For more options: python -m flight_cargo_assessment.cli --help"
"""
    
    with open("quickstart.sh", "w") as f:
        f.write(quickstart)
    
    os.chmod("quickstart.sh", 0o755)
    print("✅ Created quickstart.sh")
    
    return True


def print_next_steps():
    """Print next steps for the user"""
    print_header("Setup Complete! 🎉")
    
    print("Next steps:")
    print("\n1. Test your setup:")
    print("   python validate_bedrock_setup.py")
    
    print("\n2. Run integration tests:")
    print("   python test_bedrock_integration.py")
    
    print("\n3. Try the CLI:")
    print("   python -m flight_cargo_assessment.cli --help")
    print("   python -m flight_cargo_assessment.cli --status")
    
    print("\n4. Test AI connectivity (if using AI mode):")
    print("   python -m flight_cargo_assessment.cli --test-ai")
    
    print("\n5. Run a quick assessment:")
    print("   ./quickstart.sh")
    
    print("\n6. For development:")
    print("   python -m flight_cargo_assessment.cli --agent-mode hybrid")
    
    print("\nDocumentation:")
    print("   - README.md for detailed usage")
    print("   - .env.sample for configuration examples")
    print("   - validate_bedrock_setup.py for troubleshooting")


def main():
    """Main setup function"""
    print_header("Flight Cargo Assessment - Bedrock Setup")
    
    print("This script will help you set up the Flight Cargo Assessment system")
    print("with AWS Bedrock integration for AI-powered agents.")
    
    if not input("\nContinue with setup? (y/N): ").lower().startswith('y'):
        print("Setup cancelled.")
        return 1
    
    steps = [
        ("Python Version", check_python_version),
        ("Dependencies", install_dependencies),
        ("AWS Credentials", setup_aws_credentials),
        ("Agent Mode", configure_agent_mode),
        ("Setup Test", test_setup),
        ("Sample Files", create_sample_files)
    ]
    
    results = {}
    
    for step_name, step_func in steps:
        try:
            results[step_name] = step_func()
        except KeyboardInterrupt:
            print("\n\nSetup interrupted by user.")
            return 1
        except Exception as e:
            print(f"❌ {step_name} failed: {str(e)}")
            results[step_name] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Setup Summary")
    print("=" * 60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for step_name, result in results.items():
        status = "✅ SUCCESS" if result else "❌ FAILED"
        print(f"{step_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} steps completed")
    
    if passed >= total - 1:  # Allow one failure
        print_next_steps()
        return 0
    else:
        print("\n⚠️  Setup incomplete. Please resolve the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())