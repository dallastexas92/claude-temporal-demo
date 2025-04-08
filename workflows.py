from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy
from shared_models import ClaudePromptInput, ClaudeResponse

with workflow.unsafe.imports_passed_through():
    from activities import get_claude_response


# Set up a retry policy for the activity
retry_policy = RetryPolicy(
    maximum_attempts=3,
    initial_interval=timedelta(seconds=1),
    maximum_interval=timedelta(seconds=10),
)

"""
Workflow that sends a prompt to Claude API and returns the response.
Args:
    input: Contains the prompt, model, and max_tokens.    
Returns:
    Response from Claude API.
"""
@workflow.defn
class ClaudeWorkflow:
    @workflow.run
    async def run(self, input: ClaudePromptInput) -> ClaudeResponse:
        
        # Execute the activity to get a response from Claude
        response = await workflow.execute_activity(
            get_claude_response,
            input,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=retry_policy,
        )
        
        return response