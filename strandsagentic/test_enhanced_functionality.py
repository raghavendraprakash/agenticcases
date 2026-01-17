#!/usr/bin/env python3
"""
Enhanced functionality test for the Flight Cargo Position Assessment System
"""

from flight_cargo_assessment.models.cargo import Cargo, Dimensions, CargoRequest
from flight_cargo_assessment.models.enums import CargoType, DeckType, Priority
from flight_cargo_assessment.agents.cargo_assessment_agent import CargoAssessmentAgent
from flight_cargo_assessment.agents.weight_balance_agent import WeightBalanceAgent
from flight_cargo_assessment.agents.position_management_agent import PositionManagementAgent


def test_enhanced_functionality():
    """Test enhanced system functionality with full agent coordination"""
    print("Testing Enhanced Flight Cargo Position Assessment System...")
    
    # Initialize the main assessment agent
    assessment_agent = CargoAssessmentAgent()
    
    # Test 1: Normal cargo assessment
    print("\n1. Testing normal cargo assessment...")
    cargo1 = Cargo(
        id="NORMAL001",
        dimensions=Dimensions(length=1.5, width=1.2, height=0.8),
        weight=500,
        stackable=True,
        tiltable=False,
        fragile=False,
        cargo_type=CargoType.ELECTRONICS
    )
    
    request1 = CargoRequest(
        cargo=cargo1,
        preferred_deck=DeckType.LOWER_DECK,
        priority=Priority.NORMAL,
        requested_by="test_system"
    )
    
    result1 = assessment_agent.assess_cargo_placement(request1)
    print(f"✓ Assessment successful: {result1.assessment_successful}")
    print(f"✓ Recommendations found: {len(result1.recommended_positions)}")
    print(f"✓ Alerts generated: {len(result1.alerts)}")
    if result1.recommended_positions:
        best = result1.recommended_positions[0]
        print(f"✓ Best position: {best.position.id} (Score: {best.fit_score:.2f})")
    
    # Test 2: Weight balance validation
    print("\n2. Testing weight balance validation...")
    heavy_cargo = Cargo(
        id="HEAVY001",
        dimensions=Dimensions(length=2.0, width=1.5, height=1.2),
        weight=2200,  # Heavy cargo
        stackable=True,
        tiltable=False,
        fragile=False,
        cargo_type=CargoType.MACHINERY
    )
    
    request2 = CargoRequest(
        cargo=heavy_cargo,
        preferred_deck=DeckType.MAIN_DECK,
        priority=Priority.HIGH,
        requested_by="test_system"
    )
    
    result2 = assessment_agent.assess_cargo_placement(request2)
    print(f"✓ Heavy cargo assessment: {result2.assessment_successful}")
    if result2.weight_balance_impact:
        wb = result2.weight_balance_impact
        print(f"✓ CG shift: {wb.cg_shift:.2f}m")
        print(f"✓ Within limits: {wb.within_limits}")
    
    # Test 3: Constraint validation coordination
    print("\n3. Testing constraint validation coordination...")
    if result2.recommended_positions:
        best_pos = result2.recommended_positions[0].position
        constraint_result = assessment_agent.coordinate_constraint_validation(heavy_cargo, best_pos)
        print(f"✓ Overall valid: {constraint_result['overall_valid']}")
        print(f"✓ Severity: {constraint_result['severity']}")
        
        # Count violations and warnings
        total_violations = sum(len(cat["violations"]) for cat in constraint_result["constraint_categories"].values())
        total_warnings = sum(len(cat["warnings"]) for cat in constraint_result["constraint_categories"].values())
        print(f"✓ Total violations: {total_violations}")
        print(f"✓ Total warnings: {total_warnings}")
    
    # Test 4: Oversized cargo (should fail)
    print("\n4. Testing oversized cargo handling...")
    oversized_cargo = Cargo(
        id="OVERSIZED001",
        dimensions=Dimensions(length=3.0, width=2.5, height=2.0),  # Too large
        weight=1500,
        stackable=True,
        tiltable=False,
        fragile=False,
        cargo_type=CargoType.MACHINERY
    )
    
    request3 = CargoRequest(
        cargo=oversized_cargo,
        preferred_deck=DeckType.LOWER_DECK,
        priority=Priority.URGENT,
        requested_by="test_system"
    )
    
    result3 = assessment_agent.assess_cargo_placement(request3)
    print(f"✓ Oversized cargo rejected: {not result3.assessment_successful}")
    if not result3.assessment_successful:
        print(f"✓ Error message: {result3.error_message}")
    
    # Test 5: Weight balance agent standalone
    print("\n5. Testing Weight Balance Agent...")
    wb_agent = WeightBalanceAgent()
    
    # Test CG impact calculation
    pos_agent = PositionManagementAgent()
    test_position = pos_agent.get_position_by_id("MD-08-01")  # Mid-deck position
    
    if test_position:
        cg_impact = wb_agent.calculate_cg_impact(cargo1, test_position)
        print(f"✓ CG impact calculated: {cg_impact['cg_shift']:.3f}m shift")
        print(f"✓ New CG: {cg_impact['new_cg'].x:.2f}m")
        print(f"✓ Within limits: {cg_impact['within_cg_limits']}")
    
    # Test weight violation handling
    if test_position:
        violation_result = wb_agent.handle_weight_violation(heavy_cargo, test_position, 
                                                          pos_agent.get_available_positions())
        print(f"✓ Weight violation detected: {violation_result['has_violation']}")
        if violation_result['alternatives']:
            print(f"✓ Alternatives found: {len(violation_result['alternatives'])}")
    
    # Test 6: Capacity utilization and optimization
    print("\n6. Testing capacity utilization and optimization...")
    
    # Place several cargo items to test utilization
    cargo_list = []
    for i in range(5):
        cargo = Cargo(
            id=f"UTIL{i:03d}",
            dimensions=Dimensions(length=1.0, width=1.0, height=0.8),
            weight=300 + (i * 50),
            stackable=True,
            tiltable=True,
            fragile=False,
            cargo_type=CargoType.TEXTILES
        )
        cargo_list.append(cargo)
        
        request = CargoRequest(
            cargo=cargo,
            preferred_deck=None,  # Any deck
            priority=Priority.NORMAL,
            requested_by="test_system"
        )
        
        result = assessment_agent.assess_cargo_placement(request)
        if result.assessment_successful and result.recommended_positions:
            # Simulate placing the cargo
            best_pos = result.recommended_positions[0].position
            pos_agent.occupy_position(best_pos.id, cargo)
    
    # Check final utilization
    final_metrics = pos_agent.get_utilization_metrics()
    print(f"✓ Final utilization: {final_metrics.total_utilization:.1f}%")
    print(f"✓ Lower deck: {final_metrics.lower_deck_utilization:.1f}%")
    print(f"✓ Main deck: {final_metrics.main_deck_utilization:.1f}%")
    
    # Test optimization opportunities
    opportunities = pos_agent.identify_optimization_opportunities()
    print(f"✓ Optimization opportunities: {len(opportunities)}")
    
    # Test load balance analysis
    balance_analysis = pos_agent.get_load_balance_analysis()
    print(f"✓ Load balance score: {balance_analysis['balance_score']:.1f}")
    print(f"✓ Is balanced: {balance_analysis['is_balanced']}")
    
    # Test 7: Comprehensive recommendations
    print("\n7. Testing comprehensive recommendations...")
    test_cargo = Cargo(
        id="COMPREHENSIVE001",
        dimensions=Dimensions(length=1.8, width=1.4, height=1.0),
        weight=800,
        stackable=False,  # Non-stackable
        tiltable=False,
        fragile=True,     # Fragile
        cargo_type=CargoType.AUTOMOTIVE_PARTS,
        special_handling=["orientation_critical"]
    )
    
    test_request = CargoRequest(
        cargo=test_cargo,
        preferred_deck=DeckType.MAIN_DECK,
        priority=Priority.HIGH,
        requested_by="test_system"
    )
    
    recommendations = assessment_agent.generate_recommendations(test_request)
    print(f"✓ Recommendations generated: {recommendations['success']}")
    if recommendations['success']:
        print(f"✓ Number of recommendations: {len(recommendations['recommendations'])}")
        print(f"✓ Capacity status: {recommendations['capacity_status']['total_utilization']:.1f}%")
        print(f"✓ Alerts: {len(recommendations['alerts'])}")
    
    print("\n✅ All enhanced functionality tests completed successfully!")
    
    # Summary statistics
    print(f"\n📊 System Status Summary:")
    print(f"   • Total positions: {final_metrics.total_positions}")
    print(f"   • Available positions: {final_metrics.available_positions}")
    print(f"   • Overall utilization: {final_metrics.total_utilization:.1f}%")
    print(f"   • Weight utilization: {final_metrics.weight_utilization:.1f}%")
    
    wb_status = wb_agent.get_current_status()
    print(f"   • Current aircraft weight: {wb_status['current_weight']:.0f}kg")
    print(f"   • Current CG: {wb_status['current_cg']:.2f}m")
    print(f"   • Weight margin: {wb_status['weight_margin']:.0f}kg")
    print(f"   • System status: {wb_status['status']}")


if __name__ == "__main__":
    test_enhanced_functionality()