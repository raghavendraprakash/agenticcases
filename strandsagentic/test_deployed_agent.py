#!/usr/bin/env python3
"""
Test script for deployed Bedrock AgentCore Flight Cargo Assessment
"""

import json
import boto3
import time
import sys
from typing import Dict, Any, List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DeployedAgentTester:
    """
    Tester for deployed Bedrock Agent
    """
    
    def __init__(self, region: str = "us-east-1"):
        """
        Initialize tester
        
        Args:
            region: AWS region
        """
        self.region = region
        self.bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name=region)
        
        # Load deployment info
        self.deployment_info = self.load_deployment_info()
        
        if not self.deployment_info:
            raise ValueError("Deployment info not found. Run deployment first.")
        
        self.agent_id = self.deployment_info.get('agent_id')
        self.agent_alias_id = self.deployment_info.get('agent_alias_id')
        
        if not self.agent_id or not self.agent_alias_id:
            raise ValueError("Agent ID or Alias ID not found in deployment info")
    
    def load_deployment_info(self) -> Dict[str, Any]:
        """
        Load deployment information
        
        Returns:
            Deployment info dictionary
        """
        try:
            # Try different possible filenames
            for filename in ['deployment_info_production.json', 'deployment_info.json', 'bedrock_deployment_info.json']:
                try:
                    with open(filename, 'r') as f:
                        return json.load(f)
                except FileNotFoundError:
                    continue
            
            logger.warning("No deployment info file found")
            return {}
            
        except Exception as e:
            logger.error(f"Error loading deployment info: {e}")
            return {}
    
    def invoke_agent(self, input_text: str, session_id: str = None) -> str:
        """
        Invoke the deployed agent
        
        Args:
            input_text: Input text for the agent
            session_id: Session ID (optional)
            
        Returns:
            Agent response
        """
        if not session_id:
            session_id = f"test-session-{int(time.time())}"
        
        try:
            response = self.bedrock_agent_runtime.invoke_agent(
                agentId=self.agent_id,
                agentAliasId=self.agent_alias_id,
                sessionId=session_id,
                inputText=input_text
            )
            
            # Process streaming response
            response_text = ""
            for event in response['completion']:
                if 'chunk' in event:
                    chunk = event['chunk']
                    if 'bytes' in chunk:
                        response_text += chunk['bytes'].decode('utf-8')
            
            return response_text
            
        except Exception as e:
            logger.error(f"Error invoking agent: {e}")
            raise
    
    def test_cargo_assessment(self) -> bool:
        """
        Test cargo assessment functionality
        
        Returns:
            True if test passes
        """
        logger.info("🧪 Testing cargo assessment...")
        
        test_cargo = {
            "cargo_id": "TEST_CARGO_001",
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
        
        input_text = f"""
Please assess the following cargo for optimal position placement:

Cargo Details:
- ID: {test_cargo['cargo_id']}
- Dimensions: {test_cargo['dimensions']['length']}m × {test_cargo['dimensions']['width']}m × {test_cargo['dimensions']['height']}m
- Weight: {test_cargo['weight']} kg
- Type: {test_cargo['cargo_type']}
- Stackable: {test_cargo['stackable']}
- Fragile: {test_cargo['fragile']}
- Preferred Deck: {test_cargo['preferred_deck']}
- Priority: {test_cargo['priority']}

Please provide position recommendations with reasoning, capacity impact, and weight balance analysis.
"""
        
        try:
            response = self.invoke_agent(input_text)
            
            # Check if response contains expected elements
            expected_elements = [
                "position",
                "recommendation",
                "weight",
                "balance",
                "capacity"
            ]
            
            found_elements = sum(1 for element in expected_elements if element.lower() in response.lower())
            
            if found_elements >= 3:
                logger.info("✅ Cargo assessment test passed")
                logger.info(f"Response preview: {response[:200]}...")
                return True
            else:
                logger.warning("⚠️ Cargo assessment test failed - insufficient response elements")
                logger.info(f"Response: {response}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Cargo assessment test failed: {e}")
            return False
    
    def test_capacity_inquiry(self) -> bool:
        """
        Test capacity inquiry functionality
        
        Returns:
            True if test passes
        """
        logger.info("🧪 Testing capacity inquiry...")
        
        input_text = """
What is the current capacity status of the aircraft? Please provide:
1. Overall utilization percentage
2. Lower deck utilization
3. Main deck utilization
4. Available positions
5. Weight utilization
"""
        
        try:
            response = self.invoke_agent(input_text)
            
            # Check for capacity-related information
            capacity_indicators = [
                "utilization",
                "capacity",
                "available",
                "positions",
                "deck"
            ]
            
            found_indicators = sum(1 for indicator in capacity_indicators if indicator.lower() in response.lower())
            
            if found_indicators >= 3:
                logger.info("✅ Capacity inquiry test passed")
                logger.info(f"Response preview: {response[:200]}...")
                return True
            else:
                logger.warning("⚠️ Capacity inquiry test failed")
                logger.info(f"Response: {response}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Capacity inquiry test failed: {e}")
            return False
    
    def test_oversized_cargo(self) -> bool:
        """
        Test oversized cargo handling
        
        Returns:
            True if test passes
        """
        logger.info("🧪 Testing oversized cargo handling...")
        
        input_text = """
Please assess this oversized cargo:
- Dimensions: 20.0m × 6.0m × 4.0m
- Weight: 15000 kg
- Type: machinery
- Fragile: true
- Priority: urgent

This cargo exceeds normal aircraft limits. How should this be handled?
"""
        
        try:
            response = self.invoke_agent(input_text)
            
            # Check for appropriate rejection or alternative handling
            rejection_indicators = [
                "exceed",
                "too large",
                "cannot",
                "limit",
                "alternative",
                "not possible"
            ]
            
            found_indicators = sum(1 for indicator in rejection_indicators if indicator.lower() in response.lower())
            
            if found_indicators >= 2:
                logger.info("✅ Oversized cargo test passed")
                logger.info(f"Response preview: {response[:200]}...")
                return True
            else:
                logger.warning("⚠️ Oversized cargo test failed - should reject or suggest alternatives")
                logger.info(f"Response: {response}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Oversized cargo test failed: {e}")
            return False
    
    def test_weight_balance_concern(self) -> bool:
        """
        Test weight balance concern handling
        
        Returns:
            True if test passes
        """
        logger.info("🧪 Testing weight balance concern...")
        
        input_text = """
I need to place multiple heavy cargo items:
1. 5000 kg machinery at forward positions
2. 4000 kg automotive parts at aft positions
3. 3000 kg electronics in middle positions

What are the weight and balance implications? Are there any concerns?
"""
        
        try:
            response = self.invoke_agent(input_text)
            
            # Check for weight balance analysis
            wb_indicators = [
                "center of gravity",
                "cg",
                "balance",
                "weight distribution",
                "forward",
                "aft",
                "limit"
            ]
            
            found_indicators = sum(1 for indicator in wb_indicators if indicator.lower() in response.lower())
            
            if found_indicators >= 3:
                logger.info("✅ Weight balance concern test passed")
                logger.info(f"Response preview: {response[:200]}...")
                return True
            else:
                logger.warning("⚠️ Weight balance concern test failed")
                logger.info(f"Response: {response}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Weight balance concern test failed: {e}")
            return False
    
    def test_conversational_context(self) -> bool:
        """
        Test conversational context maintenance
        
        Returns:
            True if test passes
        """
        logger.info("🧪 Testing conversational context...")
        
        session_id = f"context-test-{int(time.time())}"
        
        try:
            # First message
            response1 = self.invoke_agent(
                "I have a 1000 kg electronics cargo, 2m × 1.5m × 1m. Where should I place it?",
                session_id
            )
            
            # Follow-up message referring to previous cargo
            response2 = self.invoke_agent(
                "What if this cargo is actually fragile? How does that change the recommendation?",
                session_id
            )
            
            # Check if second response acknowledges the context
            context_indicators = [
                "fragile",
                "electronics",
                "previous",
                "mentioned",
                "cargo",
                "change"
            ]
            
            found_indicators = sum(1 for indicator in context_indicators if indicator.lower() in response2.lower())
            
            if found_indicators >= 2:
                logger.info("✅ Conversational context test passed")
                logger.info(f"Response 1 preview: {response1[:100]}...")
                logger.info(f"Response 2 preview: {response2[:100]}...")
                return True
            else:
                logger.warning("⚠️ Conversational context test failed")
                logger.info(f"Response 2: {response2}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Conversational context test failed: {e}")
            return False
    
    def run_performance_test(self, num_requests: int = 5) -> Dict[str, float]:
        """
        Run performance test
        
        Args:
            num_requests: Number of requests to test
            
        Returns:
            Performance metrics
        """
        logger.info(f"🚀 Running performance test with {num_requests} requests...")
        
        response_times = []
        successful_requests = 0
        
        test_input = "What is the current capacity status?"
        
        for i in range(num_requests):
            start_time = time.time()
            
            try:
                response = self.invoke_agent(f"{test_input} (Request {i+1})")
                end_time = time.time()
                
                response_time = end_time - start_time
                response_times.append(response_time)
                successful_requests += 1
                
                logger.info(f"Request {i+1}: {response_time:.2f}s")
                
            except Exception as e:
                logger.error(f"Request {i+1} failed: {e}")
        
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            success_rate = successful_requests / num_requests
            
            metrics = {
                "average_response_time": avg_response_time,
                "min_response_time": min_response_time,
                "max_response_time": max_response_time,
                "success_rate": success_rate,
                "total_requests": num_requests,
                "successful_requests": successful_requests
            }
            
            logger.info("📊 Performance Metrics:")
            logger.info(f"Average Response Time: {avg_response_time:.2f}s")
            logger.info(f"Min Response Time: {min_response_time:.2f}s")
            logger.info(f"Max Response Time: {max_response_time:.2f}s")
            logger.info(f"Success Rate: {success_rate:.1%}")
            
            return metrics
        else:
            return {"error": "No successful requests"}
    
    def run_all_tests(self) -> Dict[str, bool]:
        """
        Run all test cases
        
        Returns:
            Test results
        """
        logger.info("🧪 Running comprehensive agent tests...")
        logger.info("=" * 60)
        
        tests = [
            ("Cargo Assessment", self.test_cargo_assessment),
            ("Capacity Inquiry", self.test_capacity_inquiry),
            ("Oversized Cargo", self.test_oversized_cargo),
            ("Weight Balance Concern", self.test_weight_balance_concern),
            ("Conversational Context", self.test_conversational_context)
        ]
        
        results = {}
        passed = 0
        
        for test_name, test_func in tests:
            try:
                result = test_func()
                results[test_name] = result
                if result:
                    passed += 1
                time.sleep(2)  # Brief pause between tests
            except Exception as e:
                logger.error(f"Test {test_name} failed with exception: {e}")
                results[test_name] = False
        
        # Run performance test
        try:
            perf_metrics = self.run_performance_test(3)
            results["Performance Metrics"] = perf_metrics
        except Exception as e:
            logger.error(f"Performance test failed: {e}")
            results["Performance Metrics"] = {"error": str(e)}
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("📊 Test Results Summary")
        logger.info("=" * 60)
        
        for test_name, result in results.items():
            if test_name == "Performance Metrics":
                if isinstance(result, dict) and "error" not in result:
                    logger.info(f"{test_name}: ✅ COMPLETED")
                else:
                    logger.info(f"{test_name}: ❌ FAILED")
            else:
                status = "✅ PASS" if result else "❌ FAIL"
                logger.info(f"{test_name}: {status}")
        
        logger.info(f"\nOverall: {passed}/{len(tests)} functional tests passed")
        
        if passed == len(tests):
            logger.info("🎉 All tests passed! Agent is working correctly.")
        else:
            logger.warning("⚠️ Some tests failed. Check agent configuration.")
        
        return results


def main():
    """Main test function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test deployed Bedrock Agent")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--test", choices=["all", "cargo", "capacity", "oversized", "balance", "context", "performance"], 
                       default="all", help="Specific test to run")
    parser.add_argument("--performance-requests", type=int, default=5, help="Number of requests for performance test")
    
    args = parser.parse_args()
    
    try:
        tester = DeployedAgentTester(region=args.region)
        
        if args.test == "all":
            results = tester.run_all_tests()
        elif args.test == "cargo":
            result = tester.test_cargo_assessment()
            logger.info(f"Cargo assessment test: {'✅ PASS' if result else '❌ FAIL'}")
        elif args.test == "capacity":
            result = tester.test_capacity_inquiry()
            logger.info(f"Capacity inquiry test: {'✅ PASS' if result else '❌ FAIL'}")
        elif args.test == "oversized":
            result = tester.test_oversized_cargo()
            logger.info(f"Oversized cargo test: {'✅ PASS' if result else '❌ FAIL'}")
        elif args.test == "balance":
            result = tester.test_weight_balance_concern()
            logger.info(f"Weight balance test: {'✅ PASS' if result else '❌ FAIL'}")
        elif args.test == "context":
            result = tester.test_conversational_context()
            logger.info(f"Conversational context test: {'✅ PASS' if result else '❌ FAIL'}")
        elif args.test == "performance":
            metrics = tester.run_performance_test(args.performance_requests)
            logger.info(f"Performance test completed: {metrics}")
        
    except Exception as e:
        logger.error(f"Testing failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()