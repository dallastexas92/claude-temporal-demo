import os
import anthropic
from temporalio import activity
from shared_models import ClaudePromptInput, ClaudeResponse

@activity.defn
async def get_claude_response(input: ClaudePromptInput) -> ClaudeResponse:
    """
    Activity that calls the Claude API with the given prompt.
    Args:
        input: Contains the prompt, model, max_tokens, and optional conversation history.
    Returns:
        Response from Claude API.
    """
    # Get API key from environment
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    
    # Create client
    client = anthropic.Anthropic(api_key=api_key)
    
    try:
        # Check if we have conversation history
        if input.conversation_history:
            # Use the conversation history for context
            messages = input.conversation_history
        else:
            # Just use the current prompt as a standalone message
            messages = [
                {
                    "role": "user",
                    "content": input.prompt
                }
            ]
        
        # Call Claude API
        message = client.messages.create(
            model=input.model,
            max_tokens=input.max_tokens,
            messages=messages
        )
        
        # Extract text from the response
        response_text = message.content[0].text
        
        return ClaudeResponse(
            text=response_text,
            request_id=message.id
        )
    except Exception as e:
        activity.logger.error(f"Error calling Claude API: {str(e)}")
        raise