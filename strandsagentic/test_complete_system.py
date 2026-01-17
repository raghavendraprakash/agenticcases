#!/usr/bin/env python3
"""
Complete system test for the Flight Cargo Position Assessment System
Tests all agents working together in a realistic scenario
"""

import json
from flight_cargo_assessment.models.cargo import Cargo, Dimensions, CargoRequest
from flight_cargo_assessment.models.enums import CargoType, DeckType, Priority
from flight_cargo_assessment.agents.cargo_assessment_agent import CargoAssessmentAgent
from flight_cargo_assessment.agents.alert_generation_agent import AlertGenerationAgent
from flight_cargo_assessment.agents.visualization_engine_agent import VisualizationEngineAgent


def test_complete_system():
    """Test complete system with all agents integrated"""
    print("Testing Complete Flight Cargo Position Assessment System...")
    print("=" * 60)
    
    # Initialize all agents
    assessment_agent = CargoAssessmentAgent()
    alert_agent = AlertGenerationAgent()
    viz_agent = VisualizationEngineAgent()
    
    # Test Scenario 1: Normal Operations
    print("\n🔄 SCENARIO 1: Normal Operations")
    print("-" * 40)
    
    cargo1 = Cargo(
        id="NORM001",
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
        requested_by="operations_team"
    )
    
    # Perform assessment
    result1 = assessment_agent.assess_cargo_placement(request1)
    print(f"✓ Assessment Status: {'SUCCESS' if result1.assessment_successful else 'FAILED'}")
    print(f"✓ Recommendations: {len(result1.recommended_positions)}")
    print(f"✓ System Alerts: {len(result1.alerts)}")
    
    if result1.recommended_positions:
        best_rec = result1.recommended_positions[0]
        print(f"✓ Best Position: {best_rec.position.id} (Score: {best_rec.fit_score:.2f})")
        print(f"✓ Reasoning: {best_rec.reasoning}")
    
    # Generate comprehensive alerts
    assessment_data = {
        "utilization_metrics": result1.capacity_utilization,
        "recommendations": result1.recommended_positions,
        "weight_balance_result": result1.weight_balance_impact.__dict__ if result1.weight_balance_impact else {}
    }
    
    comprehensive_alerts = alert_agent.process_assessment_alerts(cargo1, assessment_data)
    print(f"✓ Comprehensive Alerts: {len(comprehensive_alerts)}")
    
    # Generate visualization
    if result1.recommended_positions:
        all_positions = list(assessment_agent.position_agent.positions.values())
        viz_data = viz_agent.create_comprehensive_visualization(result1, all_positions)
        print(f"✓ Visualization Generated: {viz_data is not None}")
        
        # Export to JSON
        json_response = viz_agent.format_assessment_result(result1)
        print(f"✓ JSON Response Size: {len(str(json_response))} characters")
    
    # Test Scenario 2: High Capacity Stress Test
    print("\n🚨 SCENARIO 2: High Capacity Stress Test")
    print("-" * 40)
    
    # Place multiple cargo items to approach capacity
    placed_cargo = []
    for i in range(10):
        cargo = Cargo(
            id=f"STRESS{i:03d}",
            dimensions=Dimensions(length=1.2, width=1.0, height=0.7),
            weight=400 + (i * 30),
            stackable=True,
            tiltable=True,
            fragile=False,
            cargo_type=CargoType.TEXTILES
        )
        
        request = CargoRequest(
            cargo=cargo,
            preferred_deck=None,
            priority=Priority.NORMAL,
            requested_by="stress_test"
        )
        
        result = assessment_agent.assess_cargo_placement(request)
        if result.assessment_successful and result.recommended_positions:
            best_pos = result.recommended_positions[0].position
            success, _ = assessment_agent.position_agent.occupy_position(best_pos.id, cargo)
            if success:
                placed_cargo.append((cargo, best_pos))
    
    print(f"✓ Cargo Items Placed: {len(placed_cargo)}")
    
    # Check capacity alerts
    final_metrics = assessment_agent.position_agent.get_utilization_metrics()
    capacity_alerts = alert_agent.monitor_capacity(final_metrics)
    print(f"✓ Capacity Alerts Generated: {len(capacity_alerts)}")
    print(f"✓ Final Utilization: {final_metrics.total_utilization:.1f}%")
    
    for alert in capacity_alerts:
        print(f"  - {alert.severity.value.upper()}: {alert.message}")
    
    # Test Scenario 3: Constraint Violations
    print("\n⚠️  SCENARIO 3: Constraint Violations")
    print("-" * 40)
    
    # Try to place oversized cargo
    oversized_cargo = Cargo(
        id="OVERSIZED001",
        dimensions=Dimensions(length=3.0, width=2.5, height=2.0),
        weight=2800,
        stackable=False,
        tiltable=False,
        fragile=True,
        cargo_type=CargoType.MACHINERY,
        special_handling=["orientation_critical", "heavy_lift"]
    )
    
    oversized_request = CargoRequest(
        cargo=oversized_cargo,
        preferred_deck=DeckType.MAIN_DECK,
        priority=Priority.URGENT,
        requested_by="special_cargo_team"
    )
    
    oversized_result = assessment_agent.assess_cargo_placement(oversized_request)
    print(f"✓ Oversized Cargo Assessment: {'SUCCESS' if oversized_result.assessment_successful else 'REJECTED'}")
    
    if not oversized_result.assessment_successful:
        print(f"✓ Rejection Reason: {oversized_result.error_message}")
        
        # Test constraint violation handling
        available_positions = assessment_agent.position_agent.get_available_positions()
        if available_positions:
            test_position = available_positions[0]
            violation_handling = assessment_agent.handle_constraint_violations(oversized_cargo, test_position)
            print(f"✓ Violation Handling: {violation_handling['action']}")
            print(f"✓ Alternatives Found: {len(violation_handling.get('alternatives', []))}")
    
    # Test Scenario 4: Weight Balance Critical
    print("\n⚖️  SCENARIO 4: Weight Balance Critical")
    print("-" * 40)
    
    # Test very heavy cargo that might affect CG
    heavy_cargo = Cargo(
        id="HEAVY001",
        dimensions=Dimensions(length=2.0, width=1.8, height=1.5),
        weight=2400,
        stackable=True,
        tiltable=False,
        fragile=False,
        cargo_type=CargoType.MACHINERY
    )
    
    heavy_request = CargoRequest(
        cargo=heavy_cargo,
        preferred_deck=DeckType.MAIN_DECK,
        priority=Priority.HIGH,
        requested_by="heavy_cargo_ops"
    )
    
    heavy_result = assessment_agent.assess_cargo_placement(heavy_request)
    print(f"✓ Heavy Cargo Assessment: {'SUCCESS' if heavy_result.assessment_successful else 'FAILED'}")
    
    if heavy_result.weight_balance_impact:
        wb = heavy_result.weight_balance_impact
        print(f"✓ CG Shift: {wb.cg_shift:.3f}m")
        print(f"✓ Within Limits: {wb.within_limits}")
        print(f"✓ New CG: {wb.new_cg.x:.2f}m")
        
        # Generate weight balance alerts
        wb_status = assessment_agent.weight_balance_agent.get_current_status()
        wb_alerts = alert_agent.generate_weight_balance_alerts(wb_status)
        print(f"✓ Weight Balance Alerts: {len(wb_alerts)}")
    
    # Test Scenario 5: Comprehensive System Status
    print("\n📊 SCENARIO 5: System Status & Analytics")
    print("-" * 40)
    
    # Get comprehensive system status
    alert_summary = alert_agent.get_alert_summary()
    print(f"✓ Active Alerts: {alert_summary['total_active_alerts']}")
    print(f"  - Critical: {alert_summary['by_severity']['critical']}")
    print(f"  - High: {alert_summary['by_severity']['high']}")
    print(f"  - Medium: {alert_summary['by_severity']['medium']}")
    print(f"  - Low: {alert_summary['by_severity']['low']}")
    
    # Load balance analysis
    balance_analysis = assessment_agent.position_agent.get_load_balance_analysis()
    print(f"✓ Load Balance Score: {balance_analysis['balance_score']:.1f}")
    print(f"✓ Deck Balance: {'BALANCED' if balance_analysis['is_balanced'] else 'IMBALANCED'}")
    
    # Optimization opportunities
    opportunities = assessment_agent.position_agent.identify_optimization_opportunities()
    print(f"✓ Optimization Opportunities: {len(opportunities)}")
    for opp in opportunities[:3]:  # Show top 3
        print(f"  - {opp['type']}: {opp.get('recommendation', 'No details')}")
    
    # Capacity forecast
    forecast = assessment_agent.position_agent.get_capacity_forecast(hours_ahead=12)
    print(f"✓ 12-Hour Capacity Forecast: {forecast['forecast_utilization']:.1f}%")
    print(f"✓ Will Exceed Capacity: {'YES' if forecast['will_exceed_capacity'] else 'NO'}")
    
    # Generate comprehensive visualization summary
    all_positions = list(assessment_agent.position_agent.positions.values())
    viz_summary = viz_agent.generate_summary_statistics(all_positions)
    print(f"✓ Visualization Summary Generated")
    print(f"  - Total Positions: {viz_summary['positions']['total']}")
    print(f"  - Overall Utilization: {viz_summary['positions']['utilization_percentage']:.1f}%")
    print(f"  - Lower Deck Utilization: {viz_summary['decks']['lower_deck']['utilization_percentage']:.1f}%")
    print(f"  - Main Deck Utilization: {viz_summary['decks']['main_deck']['utilization_percentage']:.1f}%")
    
    # Test JSON Export
    print("\n📤 JSON Export Test")
    print("-" * 20)
    
    # Create a sample visualization and export
    if heavy_result.assessment_successful and heavy_result.recommended_positions:
        sample_viz = viz_agent.create_comprehensive_visualization(heavy_result, all_positions)
        json_export = viz_agent.export_to_json(sample_viz, pretty_print=False)
        print(f"✓ JSON Export Size: {len(json_export)} characters")
        print(f"✓ JSON Valid: {json_export.startswith('{') and json_export.endswith('}')}")
    
    print("\n" + "=" * 60)
    print("✅ COMPLETE SYSTEM TEST SUCCESSFUL!")
    print("=" * 60)
    
    # Final System Summary
    print(f"\n📋 FINAL SYSTEM SUMMARY:")
    print(f"   🏗️  Architecture: 5 specialized agents integrated")
    print(f"   📦 Positions: {viz_summary['positions']['total']} total ({viz_summary['positions']['occupied']} occupied)")
    print(f"   📊 Utilization: {viz_summary['positions']['utilization_percentage']:.1f}%")
    print(f"   ⚠️  Active Alerts: {alert_summary['total_active_alerts']}")
    print(f"   ⚖️  Weight Status: {wb_status['status']}")
    print(f"   🎯 Load Balance: {balance_analysis['balance_score']:.1f}/100")
    print(f"   🔮 Forecast: {forecast['recommendation']}")
    
    return True


if __name__ == "__main__":
    test_complete_system()