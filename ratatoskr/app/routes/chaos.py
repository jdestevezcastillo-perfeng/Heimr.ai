"""Chaos control endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models import ChaosConfig
from app.chaos.state import chaos_state
from app.chaos.scenarios import list_scenarios, get_scenario

router = APIRouter()


class ScenarioResponse(BaseModel):
    """Response from scenario activation."""
    message: str
    scenario: str
    config: ChaosConfig


class ConfigResponse(BaseModel):
    """Response from config endpoints."""
    active_scenario: str | None
    config: ChaosConfig


@router.get("/chaos/config", response_model=ConfigResponse)
async def get_chaos_config():
    """Retrieve current chaos configuration.
    
    Returns:
        Current chaos configuration and active scenario
    """
    config = await chaos_state.get_config()
    scenario = await chaos_state.get_active_scenario()
    
    return ConfigResponse(
        active_scenario=scenario,
        config=config
    )


@router.post("/chaos/config", response_model=ConfigResponse)
async def update_chaos_config(config: ChaosConfig):
    """Update chaos configuration.
    
    Supports partial updates by merging with current config.
    
    Args:
        config: New chaos configuration
        
    Returns:
        Updated chaos configuration
    """
    await chaos_state.update_config(config)
    
    updated_config = await chaos_state.get_config()
    scenario = await chaos_state.get_active_scenario()
    
    return ConfigResponse(
        active_scenario=scenario,
        config=updated_config
    )


@router.post("/chaos/scenario/{name}", response_model=ScenarioResponse)
async def activate_scenario(name: str):
    """Activate a predefined chaos scenario.
    
    Args:
        name: Scenario name (e.g., 'healthy', 'latency_spike', 'error_spike')
        
    Returns:
        Activated scenario configuration
        
    Raises:
        HTTPException: If scenario name is invalid
    """
    try:
        await chaos_state.activate_scenario(name)
        config = await chaos_state.get_config()
        
        return ScenarioResponse(
            message=f"Activated scenario: {name}",
            scenario=name,
            config=config
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/chaos/reset", response_model=ScenarioResponse)
async def reset_chaos():
    """Reset chaos to healthy baseline.
    
    Returns:
        Healthy scenario configuration
    """
    await chaos_state.reset()
    config = await chaos_state.get_config()
    
    return ScenarioResponse(
        message="Reset to healthy baseline",
        scenario="healthy",
        config=config
    )


@router.get("/chaos/scenarios")
async def get_scenarios():
    """Get list of available chaos scenarios.
    
    Returns:
        List of scenario names with descriptions
    """
    scenarios = list_scenarios()
    
    # Get descriptions for each scenario
    scenario_info = {}
    for name in scenarios:
        try:
            config = get_scenario(name)
            scenario_info[name] = {
                "name": name,
                "description": _get_scenario_description(name)
            }
        except ValueError:
            continue
    
    return {
        "scenarios": scenario_info,
        "count": len(scenario_info)
    }


def _get_scenario_description(name: str) -> str:
    """Get human-readable description for a scenario.
    
    Args:
        name: Scenario name
        
    Returns:
        Description string
    """
    descriptions = {
        "healthy": "Baseline: 50ms ± 20ms, no errors",
        "gradual_degradation": "Latency increases by 100ms/minute, max 5s",
        "latency_spike": "10% of requests get 3s delay (p99 anomalies)",
        "bimodal_latency": "90% fast (50ms), 10% slow (2s) - distribution issues",
        "error_spike": "30% error rate (mixed 5xx)",
        "rate_limited": "429s above 50 RPS",
        "cascade_failure": "Errors + latency increase with load (above 50 RPS)",
        "intermittent": "Random 5% failures (flaky behavior)",
        "connection_exhaustion": "Max 10 concurrent requests (pool exhaustion)",
        "cpu_bound": "100k hash iterations/request (CPU saturation)",
    }
    return descriptions.get(name, "No description available")
