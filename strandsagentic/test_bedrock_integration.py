#!/usr/bin/env python3
"""
Integration tests for Bedrock-powered agents
"""

import os
import sys
import json
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flight_cargo_assessment.agents.agent_factory import AgentFactory, AgentMode
from flight_cargo_assessment.models import Cargo, Dimensions, CargoRequest, DeckType, Priority, CargoType


def test_bedrock_connectivity():
    """Test basic Bedrock connectivity"""
    print("🔗 Testing Bedrock Connectivity...")
    
    try:
        # Create AI-powered factory
        factory = AgentFactory.create_production_factory()
        
        # Test connectivity
        results = factory.test_ai_connectivity()
        
        print(f"Overall Status: {results['overall_status']}")
        print(f"Bedrock Accessible: {results['bedrock_accessible']}")
        
        for model, result in results.get('models_tested', {}).items():
            status_icon = "✅" if result['status'] == 'SUCCESS' else "❌"
            print(f"{model.title()}: {status_icon} {result['status']}")
            
            if result['status'] == 'FAILED':
                print(f"  Error: {result.get('error', 'Unknown error')}")
        
        return results['overall_status'] == 'SUCCESS'
        
    except Exception as e:
        print(f"❌ Connectivity test failed: {str(e)}")
        return False


def test_ai_agent_creation():
    """Test AI agent creation and basic functionality"""
    print("\n🤖 Testing AI Agent Creation...")
    
    try:
        # Create factory
        factory = AgentFactory.create_development_factory()
        
        # Test each agent type
        agents = {
            "Position Agent": factory.create_position_agent("haiku"),
            "Weight Balance Agent": factory.create_weight_balance_agent("sonnet"),
            "Cargo Assessment Agent": factory.create_cargo_assessment_agent("sonnet")
        }
        
        for name, agent in agents.items():
            print(f"✅ {name}: {type(agent).__name__}")
            
            # Test if it's AI-powered
            if hasattr(agent, 'model_type'):
                print(f"   Model: {agent.model_type}")
            else:
                print(f"   Type: Rule-based (fallback)")
        
        return True
        
    except Exception as e:
        print(f"❌ Agent creation failed: {str(e)}")
        return False


def test_ai_cargo_assessment():
    """Test AI-powered cargo assessment"""
    print("\n📦 Testing AI Cargo Assessment...")
    
    try:
        # Create AI-powered factory
        factory = AgentFactory.create_development_factory()
        assessment_agent = factory.create_cargo_assessment_agent("sonnet")
        
        # Create test cargo
        cargo = Cargo(
            id="TEST_AI_001",
            dimensions=Dimensions(length=2.0, width=1.5, height=1.2),
            weight=800,
            stackable=True,
            tiltable=False,
            fragile=False,
            cargo_type=CargoType.ELECTRONICS
        )
        
        request = CargoRequest(
            cargo=cargo,
            preferred_deck=DeckType.LOWER_DECK,
            priority=Priority.HIGH,
            requested_by="test_user"
        )
        
        print(f"Assessing cargo: {cargo.id}")
        print(f"Dimensions: {cargo.dimensions.length}x{cargo.dimensions.width}x{cargo.dimensions.height}m")
        print(f"Weight: {cargo.weight}kg")
        
        # Perform assessment
        result = assessment_agent.assess_cargo_placement(request)
        
        print(f"Assessment Status: {'✅ SUCCESS' if result.assessment_successful else '❌ FAILED'}")
        
        if result.assessment_successful:
            print(f"Recommended Positions: {len(result.recommended_positions)}")
            if result.recommended_positions:
                top_rec = result.recommended_positions[0]
                print(f"Top Recommendation: {top_rec.position.id} (Score: {top_rec.fit_score:.2f})")
        else:
            print(f"Error: {result.error_message}")
        
        return result.assessment_successful
        
    except Exception as e:
        print(f"❌ AI assessment failed: {str(e)}")
        return False


def test_cost_estimation():
    """Test cost estimation functionality"""
    print("\n💰 Testing Cost Estimation...")
    
    try:
        factory = AgentFactory.create_production_factory()
        
        scenarios = ["light", "typical", "heavy"]
        
        for scenario in scenarios:
            cost_info = factory.get_cost_estimate(scenario)
            print(f"{scenario.title()} Usage: ${cost_info['total_monthly_cost_usd']:.2f}/month")
        
        return True
        
    except Exception as e:
        print(f"❌ Cost estimation failed: {str(e)}")
        return False


def test_hybrid_mode():
    """Test hybrid mode with fallback"""
    print("\n🔄 Testing Hybrid Mode...")
    
    try:
        # Create hybrid factory
        factory = AgentFactory.create_development_factory()
        
        # Get agent info
        info = factory.get_agent_info()
        print(f"Mode: {info['mode']}")
        print(f"Bedrock Enabled: {info['bedrock_enabled']}")
        
        # Test agent creation
        agent = factory.create_position_agent()
        print(f"Position Agent: {type(agent).__name__}")
        
        return True
        
    except Exception as e:
        print(f"❌ Hybrid mode test failed: {str(e)}")
        return False


def main():
    """Run all integration tests"""
    print("🚀 Starting Bedrock Integration Tests")
    print("=" * 50)
    
    # Check environment
    aws_region = os.getenv("AWS_REGION", "us-east-1")
    agent_mode = os.getenv("CARGO_AGENT_MODE", "rule_based")
    
    print(f"AWS Region: {aws_region}")
    print(f"Agent Mode: {agent_mode}")
    print()
    
    # Run tests
    tests = [
        ("Bedrock Connectivity", test_bedrock_connectivity),
        ("AI Agent Creation", test_ai_agent_creation),
        ("AI Cargo Assessment", test_ai_cargo_assessment),
        ("Cost Estimation", test_cost_estimation),
        ("Hybrid Mode", test_hybrid_mode)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {str(e)}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, passed_test in results.items():
        status = "✅ PASS" if passed_test else "❌ FAIL"
        print(f"{test_name}: {status}")
        if passed_test:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Bedrock integration is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check AWS credentials and Bedrock access.")
        return 1


if __name__ == "__main__":
    sys.exit(main())