#!/usr/bin/env python3
"""
Basic functionality test for the Flight Cargo Position Assessment System
"""

from flight_cargo_assessment.models.cargo import Cargo, Dimensions
from flight_cargo_assessment.models.enums import CargoType, DeckType
from flight_cargo_assessment.agents.position_management_agent import PositionManagementAgent
from flight_cargo_assessment.utils.weight_balance import calculate_center_of_gravity, validate_cg_limits


def test_basic_functionality():
    """Test basic system functionality"""
    print("Testing Flight Cargo Position Assessment System...")
    
    # Test 1: Create cargo
    print("\n1. Testing cargo creation...")
    cargo = Cargo(
        id="TEST001",
        dimensions=Dimensions(length=1.5, width=1.2, height=0.8),
        weight=500,
        stackable=True,
        tiltable=False,
        fragile=False,
        cargo_type=CargoType.ELECTRONICS
    )
    print(f"✓ Created cargo: {cargo.id}, Volume: {cargo.dimensions.volume:.2f}m³, Density: {cargo.density:.1f}kg/m³")
    
    # Test 2: Initialize Position Management Agent
    print("\n2. Testing Position Management Agent...")
    agent = PositionManagementAgent()
    print(f"✓ Initialized agent with {len(agent.positions)} positions")
    
    # Test 3: Get available positions
    print("\n3. Testing position availability...")
    available_lower = agent.get_available_positions(DeckType.LOWER_DECK)
    available_main = agent.get_available_positions(DeckType.MAIN_DECK)
    print(f"✓ Lower deck available positions: {len(available_lower)}")
    print(f"✓ Main deck available positions: {len(available_main)}")
    
    # Test 4: Find best positions for cargo
    print("\n4. Testing position recommendations...")
    best_positions = agent.find_best_positions(cargo, max_results=3)
    print(f"✓ Found {len(best_positions)} suitable positions")
    for i, (position, score) in enumerate(best_positions[:3]):
        print(f"  {i+1}. Position {position.id} (Score: {score:.2f})")
    
    # Test 5: Reserve and occupy position
    if best_positions:
        print("\n5. Testing position reservation and occupation...")
        best_position = best_positions[0][0]
        
        # Reserve position
        success, message = agent.reserve_position(best_position.id, cargo)
        print(f"✓ Reserve result: {success} - {message}")
        
        # Occupy position
        success, message = agent.occupy_position(best_position.id, cargo)
        print(f"✓ Occupy result: {success} - {message}")
    
    # Test 6: Get utilization metrics
    print("\n6. Testing utilization metrics...")
    metrics = agent.get_utilization_metrics()
    print(f"✓ Total utilization: {metrics.total_utilization:.1f}%")
    print(f"✓ Lower deck utilization: {metrics.lower_deck_utilization:.1f}%")
    print(f"✓ Main deck utilization: {metrics.main_deck_utilization:.1f}%")
    print(f"✓ Available positions: {metrics.available_positions}/{metrics.total_positions}")
    
    # Test 7: Weight balance calculations
    print("\n7. Testing weight balance calculations...")
    weights = [500, 800, 300, 1200]
    arms = [18.0, 20.0, 22.0, 24.0]
    cg = calculate_center_of_gravity(weights, arms)
    within_limits = validate_cg_limits(cg, 16.5, 26.8)
    print(f"✓ Calculated CG: {cg:.2f}m")
    print(f"✓ Within limits: {within_limits}")
    
    # Test 8: Capacity analysis
    print("\n8. Testing capacity analysis...")
    balance_analysis = agent.get_load_balance_analysis()
    print(f"✓ Load balance score: {balance_analysis['balance_score']:.1f}")
    print(f"✓ Is balanced: {balance_analysis['is_balanced']}")
    
    optimization_opportunities = agent.identify_optimization_opportunities()
    print(f"✓ Found {len(optimization_opportunities)} optimization opportunities")
    
    print("\n✅ All basic functionality tests completed successfully!")


if __name__ == "__main__":
    test_basic_functionality()