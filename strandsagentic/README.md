# Flight Cargo Position Assessment System

An intelligent cargo management solution that evaluates position availability in flight cargo compartments to accommodate loose cargo bookings. Built using Strands agents framework with Bedrock AgentCore runtime.

## Features

- **Dual-Deck Assessment**: Evaluates positions in both lower deck and main deck areas
- **Constraint Validation**: Handles stackability, tiltability, and weight distribution requirements
- **Real-time Alerts**: Prevents overbooking with intelligent alert generation
- **3D Visualization**: Provides JSON responses for cargo visualization systems
- **Agent-Based Architecture**: Scalable system using specialized agents
- **Property-Based Testing**: Comprehensive correctness validation

## Architecture

The system employs five specialized agents:

1. **Cargo Assessment Agent**: Primary orchestrator
2. **Position Management Agent**: Deck position tracking
3. **Weight Balance Agent**: Center of gravity calculations
4. **Alert Generation Agent**: Constraint monitoring
5. **Visualization Engine Agent**: Response formatting

## Installation

```bash
pip install -e .
```

## Usage

### Command Line Interface

```bash
# Single cargo assessment
cargo-assess --length 2.5 --width 1.8 --height 1.2 --weight 500 --stackable --tiltable

# Batch assessment
cargo-assess --batch cargo_requests.json

# Verbose output
cargo-assess --length 3.0 --width 2.0 --height 1.5 --weight 750 --verbose --debug
```

### Python API

```python
from flight_cargo_assessment import CargoAssessmentAgent, Cargo, Dimensions

# Create cargo request
cargo = Cargo(
    id="CARGO001",
    dimensions=Dimensions(length=2.5, width=1.8, height=1.2),
    weight=500,
    stackable=True,
    tiltable=True
)

# Assess cargo placement
agent = CargoAssessmentAgent()
result = agent.assess_cargo_placement(cargo)
```

## Development

### Running Tests

```bash
pytest tests/
```

### Property-Based Tests

```bash
pytest tests/ -k "property"
```

## Synthetic Data

The system includes comprehensive synthetic datasets:

- **Aircraft Configuration**: Boeing 777F specifications
- **Deck Positions**: 56 positions across lower and main decks
- **Cargo Types**: 5 realistic cargo categories
- **Test Scenarios**: Normal, high-capacity, and constraint violation scenarios

## License

MIT License