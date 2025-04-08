import os
import asyncio
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from temporalio.client import Client, TLSConfig
from workflows import ClaudeChatWorkflow
from shared_models import ClaudePromptInput

# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__, static_folder="static")

# Global variables
temporal_client = None


def get_temporal_client():
    """Get or create the Temporal client."""
    def _get_client_async():
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(_init_temporal_client_async())
    
    global temporal_client
    if temporal_client is not None:
        return temporal_client
    
    # Initialize client
    temporal_client = _get_client_async()
    return temporal_client


async def _init_temporal_client_async():
    """Async function to initialize the Temporal client."""
    # Get Temporal connection settings
    is_cloud = os.environ.get("TEMPORAL_ADDRESS", "").endswith("tmprl.cloud:7233")
    
    # Connect to Temporal service
    if is_cloud:
        # Connect to Temporal Cloud
        app.logger.info("Connecting to Temporal Cloud")
        client_cert_path = os.environ.get("TEMPORAL_CLIENT_CERT")
        client_key_path = os.environ.get("TEMPORAL_CLIENT_KEY")
        
        if not client_cert_path or not client_key_path:
            raise ValueError("Temporal Cloud credentials not properly configured")
        
        # Create TLS config for Temporal Cloud
        tls_config = TLSConfig(
            client_cert=open(client_cert_path, "rb").read(),
            client_private_key=open(client_key_path, "rb").read(),
        )
        
        client = await Client.connect(
            os.environ.get("TEMPORAL_ADDRESS", ""),
            namespace=os.environ.get("TEMPORAL_NAMESPACE", "default"),
            tls=tls_config,
        )
    else:
        # Connect to local Temporal server
        app.logger.info("Connecting to local Temporal server")
        client = await Client.connect("localhost:7233")
    
    return client


@app.route("/")
def index():
    """Render the main page."""
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def start_or_continue_chat():
    """API endpoint to start a new chat or continue an existing one."""
    try:
        # Get request data
        data = request.json
        if not data:
            return jsonify({"error": "Invalid JSON data"}), 400
            
        prompt = data.get("prompt")
        model = data.get("model", "claude-3-7-sonnet-20250219")
        max_tokens = data.get("maxTokens", 1024)
        conversation_id = data.get("conversationId")
        
        if not prompt:
            return jsonify({"error": "Prompt is required"}), 400
        
        # Execute the appropriate action
        if conversation_id:
            # Continue existing conversation
            result = continue_conversation(conversation_id, prompt)
        else:
            # Start new conversation
            result = start_conversation(prompt, model, max_tokens)
        
        return jsonify(result)
    
    except Exception as e:
        app.logger.error(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


def start_conversation(prompt, model, max_tokens):
    """Start a new conversation workflow."""
    def run_async():
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(_start_conversation_async(prompt, model, max_tokens))
    
    return run_async()


async def _start_conversation_async(prompt, model, max_tokens):
    """Async implementation to start a new conversation workflow."""
    # Get Temporal client
    client = await _init_temporal_client_async()
    
    # Prepare the input
    workflow_input = ClaudePromptInput(
        prompt=prompt,
        model=model,
        max_tokens=max_tokens
    )
    
    # Generate a unique workflow ID for this conversation
    conversation_id = f"claude-chat-{int(asyncio.get_event_loop().time() * 1000)}"
    
    # Start the workflow
    handle = await client.start_workflow(
        ClaudeChatWorkflow.run,
        workflow_input,
        id=conversation_id,
        task_queue="claude-queue",
    )
    
    app.logger.info(f"Started chat workflow with ID: {conversation_id}")
    
    # Wait for the first response
    # We need to query the workflow to get the response
    # First, we need to wait a bit for the workflow to process the message
    await asyncio.sleep(2)
    
    # Get the workflow handle again (now that it's been running for a bit)
    handle = client.get_workflow_handle(conversation_id)
    
    # Query the workflow for the last assistant message
    response = await handle.query(ClaudeChatWorkflow.get_last_assistant_message)
    
    return {
        "text": response,
        "conversationId": conversation_id
    }


def continue_conversation(conversation_id, message):
    """Send a new message to an existing conversation."""
    def run_async():
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(_continue_conversation_async(conversation_id, message))
    
    return run_async()


async def _continue_conversation_async(conversation_id, message):
    """Async implementation to continue an existing conversation."""
    # Get Temporal client
    client = await _init_temporal_client_async()
    
    try:
        # Get the workflow handle
        handle = client.get_workflow_handle(conversation_id)
        
        # Send the message signal
        await handle.signal(ClaudeChatWorkflow.send_message, message)
        
        # Wait a bit for the workflow to process the message
        await asyncio.sleep(2)
        
        # Query the workflow for the last assistant message
        response = await handle.query(ClaudeChatWorkflow.get_last_assistant_message)
        
        return {
            "text": response,
            "conversationId": conversation_id
        }
    except Exception as e:
        app.logger.error(f"Error sending message to workflow {conversation_id}: {str(e)}")
        return {
            "error": f"Conversation not found or error occurred: {str(e)}",
            "conversationId": conversation_id
        }


@app.route("/api/history/<conversation_id>", methods=["GET"])
def get_chat_history(conversation_id):
    """Get the full history of a conversation."""
    try:
        def run_async():
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(_get_chat_history_async(conversation_id))
        
        history = run_async()
        return jsonify(history)
    
    except Exception as e:
        app.logger.error(f"Error getting chat history: {str(e)}")
        return jsonify({"error": str(e)}), 500


async def _get_chat_history_async(conversation_id):
    """Async implementation to get chat history."""
    # Get Temporal client
    client = await _init_temporal_client_async()
    
    # Get the workflow handle
    handle = client.get_workflow_handle(conversation_id)
    
    # Query the workflow for the conversation history
    history = await handle.query(ClaudeChatWorkflow.get_conversation_history)
    
    return history

# Route to end conversation & terminate the Workflow

@app.route("/api/end-conversation/<conversation_id>", methods=["POST"])
def end_conversation(conversation_id):
    """End a conversation by terminating the workflow."""
    try:
        def run_async():
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(_end_conversation_async(conversation_id))
        
        result = run_async()
        return jsonify(result)
    
    except Exception as e:
        app.logger.error(f"Error ending conversation: {str(e)}")
        return jsonify({"error": str(e)}), 500


async def _end_conversation_async(conversation_id):
    """Async implementation to end a conversation."""
    # Get Temporal client
    client = await _init_temporal_client_async()
    
    try:
        # Get the workflow handle
        handle = client.get_workflow_handle(conversation_id)
        
        # We have two options:
        
        # Option 1: Send the end_conversation signal (preferred)
        # This lets the workflow handle its own cancellation
        await handle.signal(ClaudeChatWorkflow.end_conversation)
        
        # Option 2: Use the client's cancel method directly
        # This is more forceful and bypasses workflow cleanup logic
        # await handle.cancel()
        
        return {
            "success": True,
            "message": "Conversation ended successfully"
        }
    except Exception as e:
        app.logger.error(f"Error ending workflow {conversation_id}: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to end conversation: {str(e)}"
        }

if __name__ == "__main__":
    # Run the Flask app
    app.run(debug=True)