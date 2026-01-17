"""
AWS Lambda handler for Bedrock AgentCore Flight Cargo Assessment
"""

import json
import os
import sys
import logging
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the flight_cargo_assessment module to the path
sys.path.insert(0, '/opt/python')
sys.path.insert(0, '.')

try:
    from flight_cargo_assessment.agents.agent_factory import AgentFactory, AgentMode
    from flight_cargo_assessment.models.cargo import Cargo, Dimensions, CargoRequest, CargoType
    from flight_cargo_assessment.models.enums import DeckType, Priority
except ImportError as e:
    logger.error(f"Failed to import flight_cargo_assessment modules: {e}")
    # Fallback imports or error handling


class BedrockAgentExecutor:
    """
    Executor for Bedrock Agent actions
    """
    
    def __init__(self):
        """Initialize the executor"""
        self.agent_mode = os.getenv("CARGO_AGENT_MODE", "ai_powered")
        self.region = os.getenv("AWS_REGION", "us-east-1")
        
        # Initialize agent factory
        try:
            if self.agent_mode == "ai_powered":
                self.agent_factory = AgentFactory.create_production_factory()
            elif self.agent_mode == "hybrid":
                self.agent_factory = AgentFactory.create_development_factory()
            else:
                self.agent_factory = AgentFactory.create_rule_based_factory()
            
            # Create agents
            self.cargo_agent = self.agent_factory.create_cargo_assessment_agent()
            self.position_agent = self.agent_factory.create_position_agent()
            self.weight_balance_agent = self.agent_factory.create_weight_balance_agent()
            
            logger.info(f"Initialized agent factory in {self.agent_mode} mode")
            
        except Exception as e:
            logger.error(f"Failed to initialize agents: {e}")
            # Fallback to basic functionality
            self.agent_factory = None
            self.cargo_agent = None
    
    def assess_cargo(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess cargo placement
        
        Args:
            event_data: Cargo assessment request data
            
        Returns:
            Assessment result
        """
        try:
            logger.info(f"Processing cargo assessment request: {event_data}")
            
            # Parse cargo data
            cargo_data = event_data.get('requestBody', {})
            
            # Create cargo object
            dimensions = Dimensions(
                length=cargo_data.get('dimensions', {}).get('length', 1.0),
                width=cargo_data.get('dimensions', {}).get('width', 1.0),
                height=cargo_data.get('dimensions', {}).get('height', 1.0)
            )
            
            cargo = Cargo(
                id=cargo_data.get('cargo_id', f"BEDROCK_{int(time.time())}"),
                dimensions=dimensions,
                weight=cargo_data.get('weight', 100),
                stackable=cargo_data.get('stackable', True),
                tiltable=cargo_data.get('tiltable', True),
                fragile=cargo_data.get('fragile', False),
                cargo_type=CargoType(cargo_data.get('cargo_type', 'general'))
            )
            
            # Parse preferences
            preferred_deck = None
            if cargo_data.get('preferred_deck'):
                try:
                    preferred_deck = DeckType(cargo_data['preferred_deck'])
                except ValueError:
                    pass
            
            priority = Priority.NORMAL
            if cargo_data.get('priority'):
                try:
                    priority = Priority(cargo_data['priority'])
                except ValueError:
                    pass
            
            # Create cargo request
            request = CargoRequest(
                cargo=cargo,
                preferred_deck=preferred_deck,
                priority=priority,
                requested_by="bedrock_agent"
            )
            
            # Perform assessment
            if self.cargo_agent:
                result = self.cargo_agent.assess_cargo_placement(request)
                
                # Convert result to JSON-serializable format
                response_data = {
                    "assessment_successful": result.assessment_successful,
                    "cargo_id": result.cargo_id,
                    "recommended_positions": [
                        {
                            "position_id": rec.position.id,
                            "deck_type": rec.position.deck_type.value,
                            "fit_score": rec.fit_score,
                            "reasoning": rec.reasoning,
                            "constraints_satisfied": rec.constraints_satisfied,
                            "coordinates": {
                                "x": rec.position.coordinates.x,
                                "y": rec.position.coordinates.y,
                                "z": rec.position.coordinates.z
                            }
                        }
                        for rec in result.recommended_positions[:10]  # Limit to top 10
                    ],
                    "capacity_utilization": {
                        "total_utilization": result.capacity_utilization.total_utilization if result.capacity_utilization else 0,
                        "lower_deck_utilization": result.capacity_utilization.lower_deck_utilization if result.capacity_utilization else 0,
                        "main_deck_utilization": result.capacity_utilization.main_deck_utilization if result.capacity_utilization else 0,
                        "available_positions": result.capacity_utilization.available_positions if result.capacity_utilization else 56,
                        "total_positions": result.capacity_utilization.total_positions if result.capacity_utilization else 56
                    },
                    "weight_balance_impact": {
                        "current_cg": {
                            "x": result.weight_balance_impact.current_cg.x if result.weight_balance_impact else 20.5,
                            "y": result.weight_balance_impact.current_cg.y if result.weight_balance_impact else 0,
                            "z": result.weight_balance_impact.current_cg.z if result.weight_balance_impact else 0
                        },
                        "new_cg": {
                            "x": result.weight_balance_impact.new_cg.x if result.weight_balance_impact else 20.5,
                            "y": result.weight_balance_impact.new_cg.y if result.weight_balance_impact else 0,
                            "z": result.weight_balance_impact.new_cg.z if result.weight_balance_impact else 0
                        },
                        "within_limits": result.weight_balance_impact.within_limits if result.weight_balance_impact else True
                    } if result.weight_balance_impact else None,
                    "alerts": [
                        {
                            "severity": alert.severity.value,
                            "message": alert.message,
                            "alert_type": alert.alert_type.value,
                            "suggested_actions": alert.suggested_actions
                        }
                        for alert in result.alerts
                    ] if result.alerts else [],
                    "error_message": result.error_message
                }
                
                logger.info(f"Assessment completed successfully for cargo {cargo.id}")
                return response_data
            
            else:
                # Fallback response
                return {
                    "assessment_successful": False,
                    "cargo_id": cargo.id,
                    "error_message": "Agent not available - system in maintenance mode",
                    "recommended_positions": [],
                    "capacity_utilization": {
                        "total_utilization": 0,
                        "available_positions": 56,
                        "total_positions": 56
                    },
                    "alerts": []
                }
                
        except Exception as e:
            logger.error(f"Error in cargo assessment: {e}")
            return {
                "assessment_successful": False,
                "cargo_id": cargo_data.get('cargo_id', 'unknown'),
                "error_message": f"Assessment failed: {str(e)}",
                "recommended_positions": [],
                "capacity_utilization": {
                    "total_utilization": 0,
                    "available_positions": 56,
                    "total_positions": 56
                },
                "alerts": []
            }
    
    def get_capacity(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get current capacity status
        
        Args:
            event_data: Request data
            
        Returns:
            Capacity information
        """
        try:
            if self.position_agent:
                utilization = self.position_agent.get_utilization_metrics()
                
                return {
                    "total_utilization": utilization.total_utilization,
                    "lower_deck_utilization": utilization.lower_deck_utilization,
                    "main_deck_utilization": utilization.main_deck_utilization,
                    "available_positions": utilization.available_positions,
                    "total_positions": utilization.total_positions,
                    "weight_utilization": utilization.weight_utilization
                }
            else:
                # Fallback response
                return {
                    "total_utilization": 0.0,
                    "lower_deck_utilization": 0.0,
                    "main_deck_utilization": 0.0,
                    "available_positions": 56,
                    "total_positions": 56,
                    "weight_utilization": 0.0
                }
                
        except Exception as e:
            logger.error(f"Error getting capacity: {e}")
            return {
                "total_utilization": 0.0,
                "lower_deck_utilization": 0.0,
                "main_deck_utilization": 0.0,
                "available_positions": 56,
                "total_positions": 56,
                "weight_utilization": 0.0,
                "error": str(e)
            }
    
    def get_system_status(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get system status
        
        Args:
            event_data: Request data
            
        Returns:
            System status information
        """
        try:
            status = {
                "system_status": "operational",
                "agent_mode": self.agent_mode,
                "region": self.region,
                "agents_available": self.cargo_agent is not None,
                "timestamp": int(time.time())
            }
            
            if self.agent_factory:
                agent_info = self.agent_factory.get_agent_info()
                status.update({
                    "agent_configuration": agent_info,
                    "bedrock_enabled": agent_info.get("bedrock_enabled", False)
                })
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {
                "system_status": "error",
                "error": str(e),
                "timestamp": int(time.time())
            }


# Global executor instance
executor = BedrockAgentExecutor()


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for Bedrock Agent actions
    
    Args:
        event: Lambda event data
        context: Lambda context
        
    Returns:
        Response data
    """
    import time
    
    logger.info(f"Received event: {json.dumps(event, default=str)}")
    
    try:
        # Parse the event
        action_group = event.get('actionGroup', '')
        api_path = event.get('apiPath', '')
        http_method = event.get('httpMethod', 'GET')
        
        # Route to appropriate handler
        if api_path == '/assess-cargo' and http_method == 'POST':
            result = executor.assess_cargo(event)
        elif api_path == '/get-capacity' and http_method == 'GET':
            result = executor.get_capacity(event)
        elif api_path == '/system-status' and http_method == 'GET':
            result = executor.get_system_status(event)
        else:
            result = {
                "error": f"Unknown action: {action_group}/{api_path}",
                "available_actions": [
                    "POST /assess-cargo",
                    "GET /get-capacity",
                    "GET /system-status"
                ]
            }
        
        # Format response for Bedrock Agent
        response = {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": action_group,
                "apiPath": api_path,
                "httpMethod": http_method,
                "httpStatusCode": 200,
                "responseBody": {
                    "application/json": {
                        "body": json.dumps(result)
                    }
                }
            }
        }
        
        logger.info(f"Returning response: {json.dumps(response, default=str)}")
        return response
        
    except Exception as e:
        logger.error(f"Handler error: {e}")
        
        error_response = {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": event.get('actionGroup', ''),
                "apiPath": event.get('apiPath', ''),
                "httpMethod": event.get('httpMethod', 'GET'),
                "httpStatusCode": 500,
                "responseBody": {
                    "application/json": {
                        "body": json.dumps({
                            "error": str(e),
                            "message": "Internal server error"
                        })
                    }
                }
            }
        }
        
        return error_response


# For local testing
if __name__ == "__main__":
    # Test event
    test_event = {
        "actionGroup": "cargo-assessment",
        "apiPath": "/assess-cargo",
        "httpMethod": "POST",
        "requestBody": {
            "cargo_id": "TEST_001",
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
    }
    
    class MockContext:
        def __init__(self):
            self.function_name = "test"
            self.memory_limit_in_mb = 512
            self.invoked_function_arn = "test"
            self.aws_request_id = "test"
    
    result = handler(test_event, MockContext())
    print(json.dumps(result, indent=2))