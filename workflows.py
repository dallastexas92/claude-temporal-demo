from dataclasses import dataclass
from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy
from shared_models import ClaudePromptInput, ClaudeResponse
from typing import List, Dict, Optional
from temporalio.exceptions import ApplicationError

import time

with workflow.unsafe.imports_passed_through():
    from activities import get_claude_response


@dataclass
class ChatMessage:
    role: str  # "user" or "assistant"
    content: str
    timestamp: float


@workflow.defn
class ClaudeChatWorkflow:
    def __init__(self):
        self.messages: List[ChatMessage] = []
        self.conversation_id: Optional[str] = None
        self.model: str = "claude-3-7-sonnet-20250219"
        self.max_tokens: int = 1024
        self.last_activity: float = 0
    
    @workflow.run
    async def run(self, input: ClaudePromptInput) -> None:
        """
        Start a chat workflow and keep it running to receive more messages.
        Automatically ends after 30 minutes of inactivity.
        """
        # Store workflow settings from initial input
        self.model = input.model
        self.max_tokens = input.max_tokens
        self.last_activity = workflow.now().timestamp()
        
        try:
            # Process the first message
            await self._process_user_message(input.prompt)
            
            # Keep checking for inactivity every 5 minutes
            while True:
                try:
                    # Wait for up to 5 minutes, but will be interrupted by signals
                    await workflow.wait_condition(lambda: False, timeout=timedelta(minutes=5))
                except TimeoutError:
                    # Check for inactivity timeout (30 minutes)
                    current_time = workflow.now().timestamp()
                    if current_time - self.last_activity > 30 * 60:  # 30 minutes in seconds
                        # Conversation expired due to inactivity
                        break
                    # Otherwise continue waiting
                    continue
                except workflow.CancelledError:
                    # Workflow was explicitly cancelled (via end_conversation)
                    raise  # Re-raise to be caught by outer try/except
                
        except workflow.CancelledError:
            # Handle workflow cancellation gracefully
            pass
    
    @workflow.signal
    async def send_message(self, message: str) -> None:
        """
        Signal method to send a new message to the chat.
        
        Args:
            message: The new user message
        """
        # Process the new message
        await self._process_user_message(message)
        
        # Update last activity time
        self.last_activity = workflow.now().timestamp()
    

    @workflow.signal
    def end_conversation(self) -> None:
            """
            Signal method to explicitly end the conversation and terminate the workflow.
            This triggers workflow cancellation that will be caught in the main run method.
            """
            # Use the proper way to cancel a workflow from within
            raise ApplicationError("User requested to end the conversation")

    @workflow.query
    def get_conversation_history(self) -> List[Dict]:
        """
        Query method to get the entire conversation history.
        
        Returns:
            List of messages with role, content, and timestamp
        """
        return [
            {"role": msg.role, "content": msg.content, "timestamp": msg.timestamp}
            for msg in self.messages
        ]
    
    @workflow.query
    def get_last_assistant_message(self) -> Optional[str]:
        """
        Query method to get just the last assistant message.
        
        Returns:
            The content of the last assistant message, or None if no messages yet
        """
        for msg in reversed(self.messages):
            if msg.role == "assistant":
                return msg.content
        return None
    
    async def _process_user_message(self, message: str) -> str:
        """
        Internal method to process a user message and get a response from Claude.
        Args:
            message: The user message   
        Returns:
            Claude's response text
        """
        # Record the user message
        self.messages.append(ChatMessage(
            role="user",
            content=message,
            timestamp=workflow.now().timestamp()
        ))
        
        # Set up a retry policy for the activity
        retry_policy = RetryPolicy(
            maximum_attempts=3,
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(seconds=10),
        )
        
        # Prepare the prompt with conversation history
        # For Claude, we need to format the conversation history as messages
        messages_for_claude = [
            {"role": msg.role, "content": msg.content}
            for msg in self.messages
        ]
        
        # Call Claude with the conversation history
        response = await workflow.execute_activity(
            get_claude_response,
            ClaudePromptInput(
                prompt=message,  # Current message
                model=self.model,
                max_tokens=self.max_tokens,
                conversation_history=messages_for_claude  # Include full history
            ),
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=retry_policy,
        )
        
        # Record Claude's response
        self.messages.append(ChatMessage(
            role="assistant",
            content=response.text,
            timestamp=workflow.now().timestamp()
        ))
        
        return response.text