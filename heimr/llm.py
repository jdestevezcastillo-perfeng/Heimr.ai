import os
from typing import Dict, Any

class LLMClient:
    """
    Client for interacting with LLMs (OpenAI, Anthropic, etc.) to generate explanations.
    Currently uses a mock implementation.
    """
    def __init__(self, provider: str = "mock", base_url: str = None, model: str = None):
        self.provider = provider
        self.base_url = base_url
        self.model = model

    def generate_explanation(self, summary_stats: Dict[str, Any], anomalies_summary: Dict[str, Any]) -> str:
        """
        Generates a natural language explanation based on test stats and anomalies.
        """
        if self.provider == "mock":
            return self._generate_mock_explanation(summary_stats, anomalies_summary)
        elif self.provider == "openai":
            return self._generate_openai_explanation(summary_stats, anomalies_summary)
        elif self.provider == "anthropic":
            return self._generate_anthropic_explanation(summary_stats, anomalies_summary)
        else:
            raise NotImplementedError(f"Provider {self.provider} not implemented yet.")

    def _generate_openai_explanation(self, stats: Dict[str, Any], anomalies: Dict[str, Any]) -> str:
        try:
            from openai import OpenAI
            # For local LLMs (like Ollama), API key might not be needed, but client requires a value.
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key and self.base_url:
                api_key = "dummy-key"
            
            # Ensure api_key is not None if we are using OpenAI provider (even with custom URL)
            if not api_key:
                 # If we are here, it means no env var and no base_url (or base_url didn't trigger dummy key)
                 # But wait, if provider is openai, we expect a key.
                 # If base_url is set, we set dummy key.
                 pass

            client = OpenAI(api_key=api_key, base_url=self.base_url)
            
            prompt = self._construct_prompt(stats, anomalies)
            
            model_to_use = self.model if self.model else "gpt-4-turbo"
            
            response = client.chat.completions.create(
                model=model_to_use,
                messages=[
                    {"role": "system", "content": "You are a performance engineering expert. Analyze the following load test results."},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content
        except ImportError:
            return "Error: `openai` package not installed. Run `pip install openai`."
        except Exception as e:
            return f"Error calling OpenAI: {e}"

    def _generate_anthropic_explanation(self, stats: Dict[str, Any], anomalies: Dict[str, Any]) -> str:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
            
            prompt = self._construct_prompt(stats, anomalies)
            
            message = client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=1000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return message.content[0].text
        except ImportError:
            return "Error: `anthropic` package not installed. Run `pip install anthropic`."
        except Exception as e:
            return f"Error calling Anthropic: {e}"

    def _construct_prompt(self, stats: Dict[str, Any], anomalies: Dict[str, Any]) -> str:
        return f"""
        You are a Senior Performance Engineer. Analyze the following load test results and generate a comprehensive Root Cause Analysis (RCA) report in Markdown format.

        ### Test Statistics
        - Total Requests: {stats.get('total_requests')}
        - Average Latency: {stats.get('avg_latency'):.2f} ms
        - P99 Latency: {stats.get('p99_latency'):.2f} ms
        - Error Rate: {stats.get('error_rate'):.2f}%
        - Start Time: {stats.get('start_time')}
        - End Time: {stats.get('end_time')}

        ### Anomaly Detection Results
        - Anomalies Detected: {anomalies.get('count')}
        - Average Latency during Anomalies: {anomalies.get('avg_latency', 0):.2f} ms
        - Max Latency during Anomalies: {anomalies.get('max_latency', 0):.2f} ms
        - Anomaly Timestamps: {', '.join(str(ts) for ts in anomalies.get('timestamps', [])[:5])} ...

        ### Report Requirements
        Please structure your response exactly as follows:

        # Performance Analysis Report

        ## 1. Executive Summary
        [Provide a high-level summary of the test run. Was it successful? Did it meet SLAs? Mention the error rate and P99 latency.]

        ## 2. Detailed Analysis
        [Analyze the statistics. Discuss the significance of the P99 latency vs Average. Explain the impact of the error rate.]

        ## 3. Anomaly Investigation
        [Discuss the detected anomalies. Correlate the timestamps with potential system events. Why is the anomaly latency so high?]

        ## 4. Potential Root Causes
        [List 3-5 potential root causes based on the data. E.g., Database saturation, GC pauses, Network congestion, etc.]

        ## 5. Recommendations
        [Provide actionable next steps to resolve the issues.]
        """

    def _generate_mock_explanation(self, stats: Dict[str, Any], anomalies: Dict[str, Any]) -> str:
        """
        Returns a hardcoded mock explanation for testing.
        """
        return f"""
### 🤖 AI Analyst Report (MOCK)

**Summary**:
The load test ran for {stats.get('total_requests')} requests. 
The average latency was {stats.get('avg_latency'):.2f}ms, but the p99 latency spiked to {stats.get('p99_latency'):.2f}ms.

**Anomaly Analysis**:
I detected {anomalies.get('count')} anomalies. 
The average latency during these anomalies was {anomalies.get('avg_latency', 0):.2f}ms.

**Potential Root Causes (Hypothetical)**:
1.  **Database Locking**: The sustained latency spike suggests a database lock contention or a slow query blocking the connection pool.
2.  **Resource Saturation**: Check CPU/Memory usage on the backend pods during the anomaly window.

**Recommendations**:
-   Check database slow query logs.
-   Review connection pool settings.
"""
